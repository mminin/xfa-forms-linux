// GPL-2.0-or-later. Standalone decoder oracle/mutation driver for QA.
#include "XFAImage.h"
#include <zlib.h>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <iterator>
#include <random>
#include <string>

int main(int argc, char **argv)
{
    if (argc < 2) {
        return 2;
    }
    std::ifstream file(argv[1], std::ios::binary);
    const std::string seed((std::istreambuf_iterator<char>(file)), {});
    if (!file && seed.empty()) {
        return 2;
    }
    if (argc > 2) {
        const int iterations = std::atoi(argv[2]);
        std::mt19937 random(2123);
        for (int i = 0; i < iterations; ++i) {
            std::string data = seed;
            switch (i % 4) {
            case 0:
                data.resize(random() % (seed.size() + 1));
                break;
            case 1:
            case 2:
                for (unsigned int j = 0, n = 1 + random() % 8; j < n && !data.empty(); ++j) {
                    data[random() % data.size()] = static_cast<char>(random());
                }
                break;
            default:
                if (!data.empty()) {
                    const size_t at = random() % data.size();
                    data.insert(at, random() % 16, static_cast<char>(random()));
                }
            }
            std::cerr << argv[1] << ':' << i << std::endl;
            XFAImage image;
            if (XFADecodeImage(data, image) &&
                (image.width <= 0 || image.height <= 0 || image.data.empty())) {
                return 3;
            }
        }
        return 0;
    }
    XFAImage image;
    if (!XFADecodeImage(seed, image)) {
        return 1;
    }
    if (image.dict.find("DCTDecode") != std::string::npos) {
        std::cout << "JPEG " << image.width << ' ' << image.height << '\n';
        return 0;
    }
    const int channels = image.dict.find("/DeviceRGB") != std::string::npos ? 3 : 1;
    uLongf bytes = static_cast<uLongf>(image.width) * image.height * channels;
    std::string pixels(bytes, '\0');
    if (uncompress(reinterpret_cast<Bytef *>(pixels.data()), &bytes,
                   reinterpret_cast<const Bytef *>(image.data.data()), image.data.size()) != Z_OK || bytes != pixels.size()) {
        return 4;
    }
    uLongf alphaBytes = static_cast<uLongf>(image.width) * image.height;
    std::string alpha(alphaBytes, '\xff');
    if (!image.smask.empty() && (uncompress(reinterpret_cast<Bytef *>(alpha.data()), &alphaBytes,
            reinterpret_cast<const Bytef *>(image.smask.data()), image.smask.size()) != Z_OK || alphaBytes != alpha.size())) {
        return 4;
    }
    std::cout << "RGBA " << image.width << ' ' << image.height << '\n';
    for (size_t i = 0; i < alpha.size(); ++i) {
        std::cout.put(pixels[i * channels]);
        std::cout.put(pixels[i * channels + (channels == 3 ? 1 : 0)]);
        std::cout.put(pixels[i * channels + (channels == 3 ? 2 : 0)]);
        std::cout.put(alpha[i]);
    }
    return 0;
}
