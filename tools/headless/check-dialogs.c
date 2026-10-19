/* GPL-2.0-or-later. Synthetic integration test for Evince's XFA dialogs.
 * Run with scripts/test-dialogs.sh on a private GTK display. */
#include <evince-document.h>
#include <evince-view.h>
#include <poppler.h>
#include <glib/gstdio.h>
#include <string.h>
#include <unistd.h>

static const char *xdp =
    "<xdp:xdp xmlns:xdp=\"http://ns.adobe.com/xdp/\">"
    "<template xmlns=\"http://www.xfa.org/schema/xfa-template/3.3/\">"
    "<subform name=\"form1\" layout=\"tb\">"
    "<pageSet><pageArea name=\"Page1\"><contentArea x=\"1in\" y=\"1in\" w=\"6in\" h=\"9in\"/>"
    "<medium short=\"8.5in\" long=\"11in\"/></pageArea></pageSet>"
    "<field name=\"edit\" w=\"3in\" h=\"0.4in\"><ui><textEdit/></ui><value><text>original</text></value>"
    "<event activity=\"exit\"><script contentType=\"application/x-javascript\">"
    "if(this.rawValue==='trigger') out.rawValue=String(app.alert('Continue?',0,1,'Question'));"
    "</script></event></field>"
    "<field name=\"ask\" w=\"2in\" h=\"0.4in\"><ui><button/></ui><assist><toolTip>ask</toolTip></assist>"
    "<event activity=\"click\"><script contentType=\"application/x-javascript\">"
    "var a = xfa.host.messageBox('Continue?', 'Question', 2, Number(kind.rawValue));"
    "out.rawValue = String(a) + ':' + app.response('Which year?', 'Year', '2024');"
    "</script></event></field>"
    "<field name=\"out\" w=\"4in\" h=\"0.4in\"><ui><textEdit/></ui><assist><toolTip>out</toolTip></assist></field>"
    "<field name=\"kind\" w=\"1in\" h=\"0.4in\"><ui><textEdit/></ui><assist><toolTip>kind</toolTip></assist><value><text>2</text></value></field>"
    "</subform></template></xdp:xdp>";

static gchar *write_fixture_xdp (const char *xdp_text)
{
    const char *objects[] = {
        "<< /Type /Catalog /Pages 2 0 R /AcroForm << /Fields [] /XFA 4 0 R >> /NeedsRendering true >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>"
    };
    GString *pdf = g_string_new ("%PDF-1.7\n");
    gsize offsets[4], xref;
    gchar *path = NULL;
    GError *error = NULL;
    int fd = g_file_open_tmp ("evince-dialogs-XXXXXX.pdf", &path, &error);

    g_assert_no_error (error);
    close (fd);
    for (int i = 0; i < 3; i++) {
        offsets[i] = pdf->len;
        g_string_append_printf (pdf, "%d 0 obj\n%s\nendobj\n", i + 1, objects[i]);
    }
    offsets[3] = pdf->len;
    g_string_append_printf (pdf, "4 0 obj\n<< /Length %zu >>\nstream\n%s\nendstream\nendobj\n", strlen (xdp_text), xdp_text);
    xref = pdf->len;
    g_string_append (pdf, "xref\n0 5\n0000000000 65535 f \n");
    for (int i = 0; i < 4; i++)
        g_string_append_printf (pdf, "%010zu 00000 n \n", offsets[i]);
    g_string_append_printf (pdf, "trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n%zu\n%%%%EOF\n", xref);
    g_assert_true (g_file_set_contents (path, pdf->str, pdf->len, &error));
    g_assert_no_error (error);
    g_string_free (pdf, TRUE);
    return path;
}

static gchar *write_fixture (void)
{
    return write_fixture_xdp (xdp);
}

static GtkWidget *find_entry (GtkWidget *widget)
{
    if (GTK_IS_ENTRY (widget))
        return widget;
    for (GtkWidget *child = gtk_widget_get_first_child (widget); child;
         child = gtk_widget_get_next_sibling (child)) {
        GtkWidget *entry = find_entry (child);
        if (entry)
            return entry;
    }
    return NULL;
}

typedef struct {
    int kind;
    int answer;
    gboolean cancel_prompt;
    gboolean close_parent;
    GtkWindow *parent;
    int questions;
    int prompts;
    EvDocumentModel *replace_model;
    EvDocument *replacement;
} Answers;

static gboolean answer_dialog (gpointer user_data)
{
    Answers *answers = user_data;
    GListModel *windows = gtk_window_get_toplevels ();

    for (guint i = 0; i < g_list_model_get_n_items (windows); i++) {
        GtkWindow *window = g_list_model_get_item (windows, i);
        if (GTK_IS_DIALOG (window) && gtk_widget_get_visible (GTK_WIDGET (window))) {
            if (g_strcmp0 (gtk_window_get_title (window), "Question") == 0) {
                g_assert_true (gtk_window_get_modal (window));
                g_assert_true (gtk_window_get_transient_for (window) == answers->parent);
                g_assert_nonnull (gtk_dialog_get_widget_for_response (GTK_DIALOG (window),
                    answers->kind == 1 ? EV_FORM_ANSWER_OK : EV_FORM_ANSWER_YES));
                g_assert_cmpint (gtk_dialog_get_widget_for_response (GTK_DIALOG (window),
                    EV_FORM_ANSWER_CANCEL) != NULL, ==, answers->kind != 2);
                ++answers->questions;
                if (answers->replace_model)
                    ev_document_model_set_document (answers->replace_model, answers->replacement);
                else
                    gtk_dialog_response (GTK_DIALOG (window), answers->answer);
            } else if (g_strcmp0 (gtk_window_get_title (window), "Year") == 0) {
                GtkWidget *entry = find_entry (GTK_WIDGET (window));
                g_assert_nonnull (entry);
                g_assert_cmpstr (gtk_editable_get_text (GTK_EDITABLE (entry)), ==, "2024");
                ++answers->prompts;
                gtk_editable_set_text (GTK_EDITABLE (entry), "2026");
                if (answers->close_parent)
                    gtk_window_destroy (answers->parent);
                else
                    gtk_dialog_response (GTK_DIALOG (window), answers->cancel_prompt ?
                        GTK_RESPONSE_DELETE_EVENT : EV_FORM_ANSWER_OK);
            }
        }
        g_object_unref (window);
    }
    return G_SOURCE_CONTINUE;
}

static EvFormField *find_field (EvDocument *document, const gchar *suffix)
{
    EvPage *page = ev_document_get_page (document, 0);
    EvMappingList *mapping = ev_document_forms_get_form_fields (EV_DOCUMENT_FORMS (document), page);
    EvFormField *found = NULL;
    for (GList *l = ev_mapping_list_get_list (mapping); l; l = l->next) {
        EvFormField *field = ((EvMapping *) l->data)->data;
        PopplerFormField *poppler_field = g_object_get_data (G_OBJECT (field), "poppler-field");
        gchar *name = poppler_form_field_get_alternate_ui_name (poppler_field);
        if (name && strstr (name, suffix)) {
            found = g_object_ref (field);
            g_free (name);
            break;
        }
        g_free (name);
    }
    ev_mapping_list_unref (mapping);
    g_object_unref (page);
    g_assert_nonnull (found);
    return found;
}

static void test_dialogs (void)
{
    gchar *path = write_fixture ();
    gchar *uri = g_filename_to_uri (path, NULL, NULL);
    GError *error = NULL;
    EvDocument *document = ev_document_factory_get_document (uri, &error);
    g_assert_no_error (error);
    g_assert_nonnull (document);
    EvDocumentModel *model = ev_document_model_new ();
    GtkWidget *view = GTK_WIDGET (ev_view_new ());
    GtkWidget *window = gtk_window_new ();
    g_object_ref_sink (window);
    ev_document_model_set_document (model, document);
    ev_view_set_model (EV_VIEW (view), model);
    gtk_window_set_child (GTK_WINDOW (window), view);
    gtk_window_present (GTK_WINDOW (window));

    const int choices[] = { EV_FORM_ANSWER_NO, EV_FORM_ANSWER_YES,
        GTK_RESPONSE_DELETE_EVENT, EV_FORM_ANSWER_OK };
    const int kinds[] = { 2, 3, 1, 1 };
    const char *expected[] = { "3:2026", "4:null", "2:2026", "1:2026" };
    for (guint i = 0; i < G_N_ELEMENTS (choices); i++) {
        EvFormField *kind = find_field (document, "kind");
        gchar *text = g_strdup_printf ("%d", kinds[i]);
        ev_document_forms_form_field_text_set_text (EV_DOCUMENT_FORMS (document), kind, text);
        g_free (text);
        g_object_unref (kind);
        Answers answers = { kinds[i], choices[i], i == 1, FALSE, GTK_WINDOW (window), 0, 0, NULL, NULL };
        guint source = g_timeout_add (20, answer_dialog, &answers);
        EvFormField *ask = find_field (document, "ask");
        ev_document_forms_form_field_button_set_state (EV_DOCUMENT_FORMS (document), ask, TRUE);
        g_object_unref (ask);
        g_source_remove (source);
        g_assert_cmpint (answers.questions, ==, 1);
        g_assert_cmpint (answers.prompts, ==, 1);

        EvDocument *next = ev_document_forms_rerender (EV_DOCUMENT_FORMS (document));
        g_assert_nonnull (next);
        ev_document_model_set_document (model, next);
        g_object_unref (document);
        document = next;
        EvFormField *out = find_field (document, "out");
        text = ev_document_forms_form_field_text_get_text (EV_DOCUMENT_FORMS (document), out);
        g_assert_cmpstr (text, ==, expected[i]);
        g_free (text);
        g_object_unref (out);
    }

    /* Closing the parent while the script waits must release it with Cancel. */
    Answers closing = { 1, EV_FORM_ANSWER_OK, FALSE, TRUE, GTK_WINDOW (window), 0, 0, NULL, NULL };
    guint source = g_timeout_add (20, answer_dialog, &closing);
    EvFormField *ask = find_field (document, "ask");
    ev_document_forms_form_field_button_set_state (EV_DOCUMENT_FORMS (document), ask, TRUE);
    g_object_unref (ask);
    g_source_remove (source);
    g_assert_cmpint (closing.prompts, ==, 1);
    g_object_unref (window);
    g_object_unref (model);
    g_object_unref (document);
    g_unlink (path);
    g_free (uri);
    g_free (path);
}

/* Exercise the actual EvView focus-out commit, not a direct backend setter.
 * A file reload can replace the model while the field's script asks a question. */
static void test_editor_document_change (void)
{
    gchar *path = write_fixture ();
    gchar *uri = g_filename_to_uri (path, NULL, NULL);
    GError *error = NULL;
    EvDocument *document = ev_document_factory_get_document (uri, &error);
    g_assert_no_error (error);
    EvDocument *replacement = ev_document_factory_get_document (uri, &error);
    g_assert_no_error (error);
    EvDocumentModel *model = ev_document_model_new ();
    GtkWidget *view = GTK_WIDGET (ev_view_new ());
    GtkWidget *window = gtk_window_new ();
    GtkWidget *box = gtk_box_new (GTK_ORIENTATION_VERTICAL, 0);
    GtkWidget *button = gtk_button_new_with_label ("Leave the field");
    g_object_ref_sink (window);
    gtk_window_set_default_size (GTK_WINDOW (window), 800, 900);
    ev_document_model_set_document (model, document);
    ev_view_set_model (EV_VIEW (view), model);
    g_object_unref (document);
    gtk_widget_set_vexpand (view, TRUE);
    gtk_box_append (GTK_BOX (box), view);
    gtk_box_append (GTK_BOX (box), button);
    gtk_window_set_child (GTK_WINDOW (window), box);
    gtk_window_present (GTK_WINDOW (window));

    GtkWidget *entry = NULL;
    for (int i = 0; i < 500 && !entry; ++i) {
        while (g_main_context_iteration (NULL, FALSE)) {}
        entry = find_entry (view);
        if (!entry || g_strcmp0 (gtk_editable_get_text (GTK_EDITABLE (entry)), "original") != 0) {
            gtk_widget_child_focus (view, GTK_DIR_TAB_FORWARD);
            entry = NULL;
            g_usleep (10000);
        }
    }
    g_assert_nonnull (entry);
    g_assert_cmpstr (gtk_editable_get_text (GTK_EDITABLE (entry)), ==, "original");
    gtk_editable_set_text (GTK_EDITABLE (entry), "trigger");
    Answers answers = { 1, EV_FORM_ANSWER_CANCEL, FALSE, FALSE, GTK_WINDOW (window), 0, 0, model, replacement };
    guint source = g_timeout_add (20, answer_dialog, &answers);
    gtk_widget_grab_focus (button);
    for (int i = 0; i < 500 && !answers.questions; ++i) {
        while (g_main_context_iteration (NULL, FALSE)) {}
        g_usleep (10000);
    }
    g_source_remove (source);
    g_assert_cmpint (answers.questions, ==, 1);
    g_assert_true (ev_document_model_get_document (model) == replacement);
    gtk_window_destroy (GTK_WINDOW (window));
    g_object_unref (window);
    g_object_unref (replacement);
    g_object_unref (model);
    g_unlink (path);
    g_free (uri);
    g_free (path);
}

/* Response ids of the Security Warning dialog, matching ev-view.c. */
#define URL_BLOCK 1
#define URL_ALLOW 2

static const char *url_xdp =
    "<xdp:xdp xmlns:xdp=\"http://ns.adobe.com/xdp/\">"
    "<template xmlns=\"http://www.xfa.org/schema/xfa-template/3.3/\">"
    "<subform name=\"form1\" layout=\"tb\">"
    "<pageSet><pageArea name=\"Page1\"><contentArea x=\"1in\" y=\"1in\" w=\"6in\" h=\"9in\"/>"
    "<medium short=\"8.5in\" long=\"11in\"/></pageArea></pageSet>"
    "<field name=\"edit\" w=\"3in\" h=\"0.4in\"><ui><textEdit/></ui><value><text>original</text></value>"
    "<event activity=\"exit\"><script contentType=\"application/x-javascript\">"
    "if(this.rawValue==='go') app.launchURL('http://example.com/');"
    "</script></event></field>"
    "</subform></template></xdp:xdp>";

typedef struct {
    int response;
    gboolean remember;
    int seen;
} UrlAnswer;

static GtkWidget *find_check (GtkWidget *widget)
{
    if (GTK_IS_CHECK_BUTTON (widget))
        return widget;
    for (GtkWidget *child = gtk_widget_get_first_child (widget); child;
         child = gtk_widget_get_next_sibling (child)) {
        GtkWidget *check = find_check (child);
        if (check)
            return check;
    }
    return NULL;
}

static gboolean answer_url_dialog (gpointer user_data)
{
    UrlAnswer *answer = user_data;
    GListModel *windows = gtk_window_get_toplevels ();

    for (guint i = 0; i < g_list_model_get_n_items (windows); i++) {
        GtkWindow *window = g_list_model_get_item (windows, i);
        if (GTK_IS_DIALOG (window) && gtk_widget_get_visible (GTK_WIDGET (window)) &&
            g_strcmp0 (gtk_window_get_title (window), "Security Warning") == 0) {
            g_assert_true (gtk_window_get_modal (window));
            g_assert_nonnull (gtk_dialog_get_widget_for_response (GTK_DIALOG (window), URL_BLOCK));
            g_assert_nonnull (gtk_dialog_get_widget_for_response (GTK_DIALOG (window), URL_ALLOW));
            if (answer->remember) {
                GtkWidget *check = find_check (GTK_WIDGET (window));
                g_assert_nonnull (check);
                gtk_check_button_set_active (GTK_CHECK_BUTTON (check), TRUE);
            }
            ++answer->seen;
            gtk_dialog_response (GTK_DIALOG (window), answer->response);
        }
        g_object_unref (window);
    }
    return G_SOURCE_CONTINUE;
}

static void on_external_link (EvView *view, EvLinkAction *action, gpointer data)
{
    ++*(int *) data;
}

/* Drive the field's exit script (which calls app.launchURL) by leaving the
 * entry, then pump the loop so apply_form_changes drains the URL request. */
static void drive_url (GtkWidget *view, GtkWidget *entry, GtkWidget *button,
                       UrlAnswer *answer, int *opened)
{
    int opened_before = *opened;

    gtk_widget_grab_focus (entry);
    for (int i = 0; i < 50; ++i) {
        while (g_main_context_iteration (NULL, FALSE)) { }
        g_usleep (5000);
    }
    gtk_editable_set_text (GTK_EDITABLE (entry), "go");
    guint source = g_timeout_add (20, answer_url_dialog, answer);
    gtk_widget_grab_focus (button);
    for (int i = 0; i < 300 && answer->seen == 0 && *opened == opened_before; ++i) {
        while (g_main_context_iteration (NULL, FALSE)) { }
        g_usleep (10000);
    }
    /* Let a remembered allow open without a dialog settle too. */
    for (int i = 0; i < 20; ++i) {
        while (g_main_context_iteration (NULL, FALSE)) { }
        g_usleep (5000);
    }
    g_source_remove (source);
}

static void test_launch_url (void)
{
    gchar *path = write_fixture_xdp (url_xdp);
    gchar *uri = g_filename_to_uri (path, NULL, NULL);
    GError *error = NULL;
    EvDocument *document = ev_document_factory_get_document (uri, &error);
    g_assert_no_error (error);
    EvDocumentModel *model = ev_document_model_new ();
    GtkWidget *view = GTK_WIDGET (ev_view_new ());
    GtkWidget *window = gtk_window_new ();
    GtkWidget *box = gtk_box_new (GTK_ORIENTATION_VERTICAL, 0);
    GtkWidget *button = gtk_button_new_with_label ("Leave the field");
    int opened = 0;

    g_object_ref_sink (window);
    gtk_window_set_default_size (GTK_WINDOW (window), 800, 900);
    ev_document_model_set_document (model, document);
    ev_view_set_model (EV_VIEW (view), model);
    g_object_unref (document);
    gtk_widget_set_vexpand (view, TRUE);
    gtk_box_append (GTK_BOX (box), view);
    gtk_box_append (GTK_BOX (box), button);
    gtk_window_set_child (GTK_WINDOW (window), box);
    gtk_window_present (GTK_WINDOW (window));
    g_signal_connect (view, "external-link", G_CALLBACK (on_external_link), &opened);

    GtkWidget *entry = NULL;
    for (int i = 0; i < 500 && !entry; ++i) {
        while (g_main_context_iteration (NULL, FALSE)) { }
        entry = find_entry (view);
        if (!entry || g_strcmp0 (gtk_editable_get_text (GTK_EDITABLE (entry)), "original") != 0) {
            gtk_widget_child_focus (view, GTK_DIR_TAB_FORWARD);
            entry = NULL;
            g_usleep (10000);
        }
    }
    g_assert_nonnull (entry);

    /* Block: the warning appears and the URL is not opened. */
    UrlAnswer block = { URL_BLOCK, FALSE, 0 };
    drive_url (view, entry, button, &block, &opened);
    g_assert_cmpint (block.seen, ==, 1);
    g_assert_cmpint (opened, ==, 0);

    /* Allow, remembering the site: the URL opens once. */
    UrlAnswer allow = { URL_ALLOW, TRUE, 0 };
    drive_url (view, entry, button, &allow, &opened);
    g_assert_cmpint (allow.seen, ==, 1);
    g_assert_cmpint (opened, ==, 1);

    /* Remembered: no further warning, and the URL still opens. */
    UrlAnswer again = { URL_BLOCK, FALSE, 0 };
    drive_url (view, entry, button, &again, &opened);
    g_assert_cmpint (again.seen, ==, 0);
    g_assert_cmpint (opened, ==, 2);

    gtk_window_destroy (GTK_WINDOW (window));
    g_object_unref (window);
    g_object_unref (model);
    g_unlink (path);
    g_free (uri);
    g_free (path);
}

int main (int argc, char **argv)
{
    g_test_init (&argc, &argv, NULL);
    gtk_init ();
    g_assert_true (ev_init ());
    g_test_add_func ("/view/xfa-dialogs", test_dialogs);
    g_test_add_func ("/view/editor-document-change", test_editor_document_change);
    g_test_add_func ("/view/launch-url", test_launch_url);
    int result = g_test_run ();
    ev_shutdown ();
    return result;
}
