/* GPL-2.0-or-later. Drive the real print dialog on an isolated GTK display.
 * Always select Print to File: this test must never submit a printer job. */
#include <evince-document.h>
#include <evince-view.h>
#include <gtk/gtkunixprint.h>
#include <string.h>

static GMainLoop *loop;
static const char *action;
static const char *output;
static gboolean responded;

static gboolean
file_finished (gpointer unused)
{
    gchar *contents = NULL;
    gsize length = 0;
    gboolean complete = g_file_get_contents (output, &contents, &length, NULL) &&
        length >= 6 && memcmp (contents + length - 6, "%%EOF\n", 6) == 0;
    g_free (contents);
    if (complete)
        g_main_loop_quit (loop);
    return complete ? G_SOURCE_REMOVE : G_SOURCE_CONTINUE;
}

static gboolean
answer_dialog (gpointer unused)
{
    GListModel *windows = gtk_window_get_toplevels ();

    for (guint i = 0; i < g_list_model_get_n_items (windows); i++) {
        GtkWindow *window = g_list_model_get_item (windows, i);
        if (GTK_IS_PRINT_UNIX_DIALOG (window) && !responded) {
            GtkPrinter *printer = gtk_print_unix_dialog_get_selected_printer (GTK_PRINT_UNIX_DIALOG (window));
            if (printer && g_strcmp0 (gtk_printer_get_name (printer), "Print to File") == 0) {
                responded = TRUE;
                gtk_dialog_response (GTK_DIALOG (window),
                    g_str_equal (action, "preview") ? GTK_RESPONSE_APPLY :
                    g_str_equal (action, "cancel") ? GTK_RESPONSE_CANCEL : GTK_RESPONSE_OK);
            }
        }
        g_object_unref (window);
    }
    return G_SOURCE_CONTINUE;
}

static void
done (EvPrintOperation *op, GtkPrintOperationResult result, gpointer unused)
{
    GError *error = NULL;
    if (result == GTK_PRINT_OPERATION_RESULT_ERROR) {
        ev_print_operation_get_error (op, &error);
        g_error ("Printing failed: %s", error ? error->message : "unknown error");
    }
    g_assert_cmpint (result, ==, g_str_equal (action, "cancel") ?
        GTK_PRINT_OPERATION_RESULT_CANCEL : GTK_PRINT_OPERATION_RESULT_APPLY);
    g_assert_true (responded);
    /* GTK's direct-print "done" precedes the asynchronous file-backend copy.
     * Keep servicing the main context until the destination PDF is complete. */
    if (g_str_equal (action, "file"))
        g_timeout_add (100, file_finished, NULL);
    else
        g_main_loop_quit (loop);
}

static gboolean
timed_out (gpointer unused)
{
    g_error ("Print dialog/operation timed out");
    return G_SOURCE_REMOVE;
}

int main (int argc, char **argv)
{
    GError *error = NULL;
    g_autofree gchar *input_uri = NULL;
    g_autofree gchar *output_uri = NULL;
    EvDocument *document;
    EvPrintOperation *op;
    GtkPrintSettings *settings;
    GtkWindow *window;
    guint answer_source, timeout_source;

    g_assert_cmpint (argc, ==, 4);
    action = argv[1];
    output = argv[3];
    g_assert_true (g_str_equal (action, "preview") || g_str_equal (action, "file") || g_str_equal (action, "cancel"));
    g_set_prgname ("check-printing");
    g_set_application_name ("Printing regression");
    gtk_init ();
    g_assert_true (ev_init ());
    input_uri = g_filename_to_uri (argv[2], NULL, &error);
    g_assert_no_error (error);
    output_uri = g_filename_to_uri (argv[3], NULL, &error);
    g_assert_no_error (error);
    document = ev_document_factory_get_document (input_uri, &error);
    g_assert_no_error (error);
    g_assert_nonnull (document);
    op = ev_print_operation_new (document);
    g_assert_nonnull (op);
    settings = gtk_print_settings_new ();
    gtk_print_settings_set_printer (settings, "Print to File");
    gtk_print_settings_set (settings, GTK_PRINT_SETTINGS_OUTPUT_URI, output_uri);
    gtk_print_settings_set (settings, GTK_PRINT_SETTINGS_OUTPUT_FILE_FORMAT, "pdf");
    ev_print_operation_set_print_settings (op, settings);
    ev_print_operation_set_job_name (op, "Printing regression");
    g_object_unref (settings);
    window = GTK_WINDOW (gtk_window_new ());
    gtk_window_present (window);
    loop = g_main_loop_new (NULL, FALSE);
    g_signal_connect (op, "done", G_CALLBACK (done), NULL);
    answer_source = g_timeout_add (100, answer_dialog, NULL);
    timeout_source = g_timeout_add_seconds (25, timed_out, NULL);
    ev_print_operation_run (op, window);
    g_main_loop_run (loop);
    g_source_remove (answer_source);
    g_source_remove (timeout_source);
    ev_job_scheduler_wait ();
    gtk_window_destroy (window);
    g_object_unref (op);
    g_object_unref (document);
    g_main_loop_unref (loop);
    ev_shutdown ();
    return 0;
}
