#!/bin/sh
# Fills in the Government of Canada consent letter form (form 2123, see
# README) with made-up data, clicks "Generate letter" and writes the result:
# an end-to-end test of the XFA engine through pdfxfa.
# Usage: tools/consent-letter-scenario.sh out.pdf [-print]
# The form is read from samples/consent-letter-2123.pdf, or from $FORM.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=${1:-/tmp/consent-letter.pdf}
shift || true
export LD_LIBRARY_PATH="$ROOT/_build/poppler:$LD_LIBRARY_PATH"
M=English.MainForm
exec "$ROOT/_build/poppler/utils/pdfxfa" -log "$@" \
    -set "$M.PersonGivingConsent.PersonGivingConsentInfo.Names.givingName=Jane Example" \
    -set "$M.PersonGivingConsent.GivingAddress.streetAddress=123 Sample Street" \
    -set "$M.PersonGivingConsent.GivingAddress.city=Springfield" \
    -set "$M.PersonGivingConsent.GivingAddress.province=British Columbia" \
    -set "$M.PersonGivingConsent.GivingAddress.country=Canada" \
    -set "$M.PersonGivingConsent.GivingAddress.telephone1=250-555-0100" \
    -set "$M.PersonGivingConsent.GivingAddress.email=jane@example.org" \
    -set "$M.ConsentOfName.ChNames.ConsentOf.childName=Alex Example" \
    -set "$M.ConsentOfName.ChildDetails.ChildInfo.childPlaceBirth=Victoria, BC" \
    -set "$M.ConsentOfName.ChildDetails.ChildInfo.childBirthDate=2016-04-02" \
    -set "$M.ConsentOfName.ChildDetails.ChildInfo.GenderCH.rbChildGender=FEMALE" \
    -set "$M.ConsentOfName.ChildDetails.ChildInfo.ChPassport.rbChPassport=YES" \
    -set "$M.ConsentOfName.ChildDetails.ChildInfo.ChPassport.ChildPassportInfo.childPassportNumber=AB123456" \
    -set "$M.ConsentOfName.ChildDetails.ChildInfo.ChPassport.ChildPassportInfo.childPassportDate=2024-01-15" \
    -set "$M.ConsentOfName.ChildDetails.ChildInfo.ChPassport.ChildPassportInfo.childPassportCountry=Canada" \
    -set "$M.ConsentOfName.ChildDetails.ChildInfo.ChBirthCert.rbChBirthCert=NO" \
    -set "$M.AccompanyingPersonDetails.Accompany.rbTravelAlone=ACCOMPANIED" \
    -set "$M.AccompanyingPersonDetails.AccPersonInfo.AccPersonName=Sam Example" \
    -set "$M.AccompanyingPersonDetails.AccPersonInfo.relationShipto=Father" \
    -set "$M.AccompanyingPersonDetails.AccPersonInfo.AccPersonPassportNumber=CD654321" \
    -set "$M.AccompanyingPersonDetails.AccPersonInfo.AccPersonPassportDate=2022-06-30" \
    -set "$M.AccompanyingPersonDetails.AccPersonInfo.AccPersonPassportCountry=Canada" \
    -set "$M.ContactDuringTrip.DayTrip.dayTrip=NO" \
    -set "$M.ContactDuringTrip.MultipleCountries.rbMultipleCountries=NO" \
    -set "$M.ContactDuringTrip.TripAddressSingle.CountryVisiting.tripCountry=Mexico" \
    -set "$M.ContactDuringTrip.TripAddressSingle.CountryVisiting.givingName=Maria Example" \
    -set "$M.ContactDuringTrip.TripAddressSingle.CountryVisiting.streetAddress=1 Calle Ejemplo" \
    -set "$M.ContactDuringTrip.TripAddressSingle.CountryVisiting.city=Oaxaca" \
    -set "$M.ContactDuringTrip.TripAddressSingle.CountryVisiting.province=Oaxaca" \
    -set "$M.ContactDuringTrip.TripAddressSingle.CountryVisiting.telephone1=+52 555 0100" \
    -set "$M.ContactDuringTrip.TripAddressSingle.CountryVisiting.email=maria@example.org" \
    -set "$M.PerionOf.departureDate=2026-12-20" \
    -set "$M.PerionOf.returnDate=2027-01-05" \
    -set "$M.WitnessOrCert.rbSignedCert=SIGNED" \
    -set "English.GenerateButtons.paperSize=LETTER" \
    -click "English.GenerateButtons.filledLetter" \
    "${FORM:-$ROOT/samples/consent-letter-2123.pdf}" "$OUT"
