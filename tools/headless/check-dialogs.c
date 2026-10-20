/* GPL-2.0-or-later. Synthetic integration test for Evince's XFA dialogs.
 * Run with scripts/test-dialogs.sh on a private GTK display. */
#include <evince-document.h>
#include <evince-view.h>
#include <poppler.h>
#include <glib/gstdio.h>
#include <string.h>
#include <unistd.h>
#include <gmodule.h>
#ifdef GDK_WINDOWING_X11
#include <gdk/x11/gdkx.h>
#include <X11/keysym.h>
#endif

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
static void test_editor_document_change (gconstpointer data)
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
    if (GPOINTER_TO_INT (data))
        ev_view_commit_form_fields (EV_VIEW (view));
    else
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

typedef struct {
    int count;
    gchar *site;
    gboolean allowed;
} Remembered;

static void on_site_remembered (EvView *view, const gchar *site, gboolean allowed, gpointer data)
{
    Remembered *remembered = data;
    ++remembered->count;
    g_free (remembered->site);
    remembered->site = g_strdup (site);
    remembered->allowed = allowed;
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
    Remembered remembered = { 0, NULL, FALSE };

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
    g_signal_connect (view, "form-url-site-remembered", G_CALLBACK (on_site_remembered), &remembered);

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
    g_assert_cmpint (remembered.count, ==, 1);
    g_assert_cmpstr (remembered.site, ==, "example.com");
    g_assert_true (remembered.allowed);

    /* Remembered: no further warning, and the URL still opens. */
    UrlAnswer again = { URL_BLOCK, FALSE, 0 };
    drive_url (view, entry, button, &again, &opened);
    g_assert_cmpint (again.seen, ==, 0);
    g_assert_cmpint (opened, ==, 2);

    /* Sites kept by the application replace the remembered ones, and match
     * without regard to case: a blocked site opens nothing, silently. */
    const gchar *blocked[] = { "Example.COM", NULL };
    ev_view_set_form_url_sites (EV_VIEW (view), NULL, blocked);
    UrlAnswer listed = { URL_ALLOW, FALSE, 0 };
    drive_url (view, entry, button, &listed, &opened);
    g_assert_cmpint (listed.seen, ==, 0);
    g_assert_cmpint (opened, ==, 2);

    /* Unlisted sites follow the policy. */
    ev_view_set_form_url_sites (EV_VIEW (view), NULL, NULL);
    ev_view_set_form_url_policy (EV_VIEW (view), EV_FORM_URL_POLICY_ALLOW);
    UrlAnswer open_all = { URL_BLOCK, FALSE, 0 };
    drive_url (view, entry, button, &open_all, &opened);
    g_assert_cmpint (open_all.seen, ==, 0);
    g_assert_cmpint (opened, ==, 3);
    ev_view_set_form_url_policy (EV_VIEW (view), EV_FORM_URL_POLICY_BLOCK);
    UrlAnswer block_all = { URL_ALLOW, FALSE, 0 };
    drive_url (view, entry, button, &block_all, &opened);
    g_assert_cmpint (block_all.seen, ==, 0);
    g_assert_cmpint (opened, ==, 3);
    g_assert_cmpint (remembered.count, ==, 1);
    g_free (remembered.site);

    gtk_window_destroy (GTK_WINDOW (window));
    g_object_unref (window);
    g_object_unref (model);
    g_unlink (path);
    g_free (uri);
    g_free (path);
}

static const char *tab_xdp =
    "<xdp:xdp xmlns:xdp=\"http://ns.adobe.com/xdp/\">"
    "<template xmlns=\"http://www.xfa.org/schema/xfa-template/3.3/\">"
    "<subform name=\"form1\" layout=\"tb\">"
    "<pageSet><pageArea name=\"Page1\"><contentArea x=\"1in\" y=\"1in\" w=\"6in\" h=\"9in\"/>"
    "<medium short=\"8.5in\" long=\"11in\"/></pageArea></pageSet>"
    "<field name=\"a\" w=\"3in\" h=\"0.4in\"><ui><textEdit%s/></ui><value><text>first</text></value></field>"
    "</subform></template></xdp:xdp>";

/* Ctrl+wheel zooms in the view's scroll controller. A GTK 4 scroll controller
 * without axes never emits scroll, so the zoom silently stopped working. */
static void test_ctrl_wheel_zoom (void)
{
    GtkWidget *view = g_object_ref_sink (GTK_WIDGET (ev_view_new ()));
    GListModel *controllers = gtk_widget_observe_controllers (view);
    gboolean found = FALSE;

    for (guint i = 0; i < g_list_model_get_n_items (controllers); ++i) {
        GObject *controller = g_list_model_get_item (controllers, i);
        if (GTK_IS_EVENT_CONTROLLER_SCROLL (controller)) {
            GtkEventControllerScrollFlags flags = gtk_event_controller_scroll_get_flags (GTK_EVENT_CONTROLLER_SCROLL (controller));
            g_assert_true (flags & GTK_EVENT_CONTROLLER_SCROLL_VERTICAL);
            g_assert_true (flags & GTK_EVENT_CONTROLLER_SCROLL_HORIZONTAL);
            found = TRUE;
        }
        g_object_unref (controller);
    }
    g_assert_true (found);
    g_object_unref (controllers);
    g_object_unref (view);
}

static GtkWidget *find_text_view (GtkWidget *widget);
static gchar *text_view_text (GtkWidget *widget);

/* Tab saves the field being left only once GTK has finished moving the focus.
 * With a single field, Tab comes back to it and opens its editor before the
 * new value is saved, and the form needs no new layout. The editor must then
 * show the saved value, not the one it opened with. */
static void test_tab_refresh (gconstpointer data)
{
    gboolean multiline = GPOINTER_TO_INT (data);
    gchar *fixture = g_strdup_printf (tab_xdp, multiline ? " multiLine=\"1\"" : "");
    gchar *path = write_fixture_xdp (fixture);
    g_free (fixture);
    gchar *uri = g_filename_to_uri (path, NULL, NULL);
    GError *error = NULL;
    EvDocument *document = ev_document_factory_get_document (uri, &error);
    g_assert_no_error (error);
    EvDocumentModel *model = ev_document_model_new ();
    GtkWidget *view = GTK_WIDGET (ev_view_new ());
    GtkWidget *window = gtk_window_new ();

    g_object_ref_sink (window);
    gtk_window_set_default_size (GTK_WINDOW (window), 800, 900);
    ev_document_model_set_document (model, document);
    ev_view_set_model (EV_VIEW (view), model);
    g_object_unref (document);
    gtk_window_set_child (GTK_WINDOW (window), view);
    gtk_window_present (GTK_WINDOW (window));

    GtkWidget *entry = NULL;
    for (int i = 0; i < 500 && !entry; ++i) {
        while (g_main_context_iteration (NULL, FALSE)) { }
        entry = multiline ? find_text_view (view) : find_entry (view);
        gchar *shown = entry ? (multiline ? text_view_text (entry) :
            g_strdup (gtk_editable_get_text (GTK_EDITABLE (entry)))) : NULL;
        if (g_strcmp0 (shown, "first") != 0) {
            gtk_widget_child_focus (view, GTK_DIR_TAB_FORWARD);
            entry = NULL;
            g_usleep (10000);
        }
        g_free (shown);
    }
    g_assert_nonnull (entry);
    if (multiline)
        gtk_text_buffer_set_text (gtk_text_view_get_buffer (GTK_TEXT_VIEW (entry)), "copied", -1);
    else
        gtk_editable_set_text (GTK_EDITABLE (entry), "copied");
    gtk_widget_child_focus (window, GTK_DIR_TAB_FORWARD);

    GtkWidget *next = NULL;
    for (int i = 0; i < 300; ++i) {
        while (g_main_context_iteration (NULL, FALSE)) { }
        next = multiline ? find_text_view (view) : find_entry (view);
        gchar *shown = next ? (multiline ? text_view_text (next) :
            g_strdup (gtk_editable_get_text (GTK_EDITABLE (next)))) : NULL;
        gboolean refreshed = next && next != entry && g_strcmp0 (shown, "copied") == 0;
        g_free (shown);
        if (refreshed)
            break;
        g_usleep (10000);
    }
    g_assert_nonnull (next);
    g_assert_true (next != entry);
    gchar *shown = multiline ? text_view_text (next) : g_strdup (gtk_editable_get_text (GTK_EDITABLE (next)));
    g_assert_cmpstr (shown, ==, "copied");
    g_free (shown);

    gtk_window_destroy (GTK_WINDOW (window));
    g_object_unref (window);
    g_object_unref (model);
    g_unlink (path);
    g_free (uri);
    g_free (path);
}

static GtkWidget *find_text_view (GtkWidget *widget)
{
    if (GTK_IS_TEXT_VIEW (widget))
        return widget;
    for (GtkWidget *child = gtk_widget_get_first_child (widget); child;
         child = gtk_widget_get_next_sibling (child)) {
        GtkWidget *text = find_text_view (child);
        if (text)
            return text;
    }
    return NULL;
}

static gchar *text_view_text (GtkWidget *widget)
{
    GtkTextBuffer *buffer = gtk_text_view_get_buffer (GTK_TEXT_VIEW (widget));
    GtkTextIter start, end;
    gtk_text_buffer_get_bounds (buffer, &start, &end);
    return gtk_text_buffer_get_text (buffer, &start, &end, FALSE);
}

/* IRCC name fields are multiline even when the answer fits on one line.
 * Exercise their real editor, focus-out save, XFA rerender and reopening. */
static void test_multiline_editor (void)
{
    const char *multiline_xdp =
        "<xdp:xdp xmlns:xdp=\"http://ns.adobe.com/xdp/\">"
        "<template xmlns=\"http://www.xfa.org/schema/xfa-template/3.3/\">"
        "<subform name=\"form1\" layout=\"tb\">"
        "<pageSet><pageArea><contentArea x=\"1in\" y=\"1in\" w=\"6in\" h=\"9in\"/>"
        "<medium short=\"8.5in\" long=\"11in\"/></pageArea></pageSet>"
        "<field name=\"name\" w=\"3in\" h=\"0.8in\"><ui><textEdit multiLine=\"1\"/></ui>"
        "<assist><toolTip>name</toolTip></assist><value><text>Original</text></value>"
        "<event activity=\"exit\"><script contentType=\"application/x-javascript\">"
        "out.rawValue=this.rawValue;</script></event></field>"
        "<field name=\"out\" w=\"3in\" h=\"0.8in\" access=\"nonInteractive\"><ui><textEdit/></ui></field>"
        "</subform></template></xdp:xdp>";
    gchar *path = write_fixture_xdp (multiline_xdp);
    gchar *uri = g_filename_to_uri (path, NULL, NULL);
    GError *error = NULL;
    EvDocument *document = ev_document_factory_get_document (uri, &error);
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

    const char *expected[] = { "Original", "Jane\nDoe", "jane\nDoe", "" };
    for (guint round = 0; round < G_N_ELEMENTS (expected); ++round) {
        GtkWidget *editor = NULL;
        for (int i = 0; i < 500 && !editor; ++i) {
            while (g_main_context_iteration (NULL, FALSE)) { }
            editor = find_text_view (view);
            if (!editor) {
                gtk_widget_child_focus (view, GTK_DIR_TAB_FORWARD);
                g_usleep (10000);
            }
        }
        g_assert_nonnull (editor);
        gchar *shown = text_view_text (editor);
        g_assert_cmpstr (shown, ==, round ? expected[round - 1] : "Original");
        g_free (shown);
        g_assert_false (gtk_text_view_get_accepts_tab (GTK_TEXT_VIEW (editor)));
        gtk_text_buffer_set_text (gtk_text_view_get_buffer (GTK_TEXT_VIEW (editor)), expected[round], -1);
        document = g_object_ref (ev_document_model_get_document (model));
        gtk_widget_grab_focus (button);
        for (int i = 0; i < 500; ++i) {
            while (g_main_context_iteration (NULL, FALSE)) { }
            if (round == 0 || ev_document_model_get_document (model) != document)
                break;
            g_usleep (10000);
        }
        if (round)
            g_assert_true (ev_document_model_get_document (model) != document);
        g_object_unref (document);
        document = ev_document_model_get_document (model);
        EvFormField *field = find_field (document, "name");
        gchar *saved = ev_document_forms_form_field_text_get_text (EV_DOCUMENT_FORMS (document), field);
        g_assert_cmpstr (saved ? saved : "", ==, expected[round]);
        g_free (saved);
        g_object_unref (field);
        if (round) {
            EvPage *page = ev_document_get_page (document, 0);
            gchar *text = ev_document_text_get_text (EV_DOCUMENT_TEXT (document), page);
            g_assert_true (round == 3 || strstr (text, round == 1 ? "Jane" : "jane") != NULL);
            g_free (text);
            g_object_unref (page);
        }
        gtk_widget_grab_focus (view);
    }

    gtk_window_destroy (GTK_WINDOW (window));
    g_object_unref (window);
    g_object_unref (model);
    g_unlink (path);
    g_free (uri);
    g_free (path);
}

typedef struct {
    gchar *path, *uri;
    EvDocumentModel *model;
    GtkWidget *window, *view, *button;
} EditingFixture;

static void spin_editing (void)
{
    for (int i = 0; i < 30; ++i) {
        while (g_main_context_iteration (NULL, FALSE)) { }
        g_usleep (10000);
    }
}

static GtkWidget *find_widget_type (GtkWidget *widget, GType type)
{
    if (G_TYPE_CHECK_INSTANCE_TYPE (widget, type))
        return widget;
    for (GtkWidget *child = gtk_widget_get_first_child (widget); child;
         child = gtk_widget_get_next_sibling (child)) {
        GtkWidget *found = find_widget_type (child, type);
        if (found)
            return found;
    }
    return NULL;
}

static EditingFixture editing_fixture (const gchar *fields)
{
    gchar *fixture = g_strconcat (
        "<xdp:xdp xmlns:xdp=\"http://ns.adobe.com/xdp/\">"
        "<template xmlns=\"http://www.xfa.org/schema/xfa-template/3.3/\">"
        "<subform name=\"form1\" layout=\"tb\">"
        "<pageSet><pageArea><contentArea x=\"1in\" y=\"1in\" w=\"6in\" h=\"9in\"/>"
        "<medium short=\"8.5in\" long=\"11in\"/></pageArea></pageSet>",
        fields, "</subform></template></xdp:xdp>", NULL);
    EditingFixture f = { 0 };
    f.path = write_fixture_xdp (fixture);
    g_free (fixture);
    f.uri = g_filename_to_uri (f.path, NULL, NULL);
    GError *error = NULL;
    EvDocument *document = ev_document_factory_get_document (f.uri, &error);
    g_assert_no_error (error);
    f.model = ev_document_model_new ();
    f.view = GTK_WIDGET (ev_view_new ());
    f.window = g_object_ref_sink (gtk_window_new ());
    f.button = gtk_button_new_with_label ("Leave the field");
    GtkWidget *box = gtk_box_new (GTK_ORIENTATION_VERTICAL, 0);
    gtk_window_set_default_size (GTK_WINDOW (f.window), 800, 900);
    ev_document_model_set_document (f.model, document);
    ev_view_set_model (EV_VIEW (f.view), f.model);
    g_object_unref (document);
    gtk_widget_set_vexpand (f.view, TRUE);
    gtk_box_append (GTK_BOX (box), f.view);
    gtk_box_append (GTK_BOX (box), f.button);
    gtk_window_set_child (GTK_WINDOW (f.window), box);
    gtk_window_present (GTK_WINDOW (f.window));
    spin_editing ();
    return f;
}

static GtkWidget *editing_open (EditingFixture *f, GType type)
{
    for (int i = 0; i < 50; ++i) {
        GtkWidget *editor = find_widget_type (f->view, type);
        if (editor)
            return editor;
        gtk_widget_child_focus (f->view, GTK_DIR_TAB_FORWARD);
        spin_editing ();
    }
    g_error ("No editor of type %s", g_type_name (type));
    return NULL;
}

static void editing_assert_value (EditingFixture *f, const gchar *label, const gchar *expected)
{
    EvDocument *doc = ev_document_model_get_document (f->model);
    EvFormField *field = find_field (doc, label);
    gchar *value = EV_IS_FORM_FIELD_CHOICE (field) ?
        ev_document_forms_form_field_choice_get_text (EV_DOCUMENT_FORMS (doc), field) :
        ev_document_forms_form_field_text_get_text (EV_DOCUMENT_FORMS (doc), field);
    g_assert_cmpstr (value ? value : "", ==, expected);
    g_free (value);
    g_object_unref (field);
}

static void editing_free (EditingFixture *f)
{
    gtk_window_destroy (GTK_WINDOW (f->window));
    g_object_unref (f->window);
    spin_editing ();
    g_object_unref (f->model);
    g_unlink (f->path);
    g_free (f->path);
    g_free (f->uri);
}

static void editing_assert_choice (EditingFixture *f, int selected)
{
    EvDocument *document = ev_document_model_get_document (f->model);
    EvFormField *field = find_field (document, "choice");
    for (int i = 0; i < 2; ++i)
        g_assert_cmpint (ev_document_forms_form_field_choice_is_item_selected (
                            EV_DOCUMENT_FORMS (document), field, i), ==, i == selected);
    g_object_unref (field);
}

/* Real, held mouse clicks matter here: sending press and release in one
 * batch misses editors appearing beneath the pointer between events. */
static void test_mouse_choice (void)
{
#ifdef GDK_WINDOWING_X11
    if (!GDK_IS_X11_DISPLAY (gdk_display_get_default ())) {
        g_test_skip ("Mouse regression requires a private X11 display");
        return;
    }
    GModule *x11 = g_module_open ("libX11.so.6", G_MODULE_BIND_LAZY | G_MODULE_BIND_LOCAL);
    GModule *xtst = g_module_open ("libXtst.so.6", G_MODULE_BIND_LAZY | G_MODULE_BIND_LOCAL);
    if (!x11 || !xtst) {
        if (x11) g_module_close (x11);
        if (xtst) g_module_close (xtst);
        g_test_skip ("Mouse regression requires libXtst.so.6");
        return;
    }
    Bool (*motion) (Display *, int, int, int, unsigned long);
    Bool (*button) (Display *, unsigned int, Bool, unsigned long);
    Bool (*key) (Display *, unsigned int, Bool, unsigned long);
    int (*flush) (Display *);
    KeyCode (*keycode) (Display *, KeySym);
    Bool (*translate) (Display *, Window, Window, int, int, int *, int *, Window *);
    g_assert_true (g_module_symbol (xtst, "XTestFakeMotionEvent", (gpointer *) &motion));
    g_assert_true (g_module_symbol (xtst, "XTestFakeButtonEvent", (gpointer *) &button));
    g_assert_true (g_module_symbol (xtst, "XTestFakeKeyEvent", (gpointer *) &key));
    g_assert_true (g_module_symbol (x11, "XFlush", (gpointer *) &flush));
    g_assert_true (g_module_symbol (x11, "XKeysymToKeycode", (gpointer *) &keycode));
    g_assert_true (g_module_symbol (x11, "XTranslateCoordinates", (gpointer *) &translate));
    EditingFixture f = editing_fixture (
        "<field name=\"lead\" w=\"3in\" h=\"0.4in\"><ui><textEdit/></ui></field>"
        "<field name=\"choice\" w=\"3in\" h=\"0.4in\"><assist><toolTip>choice</toolTip></assist>"
        "<ui><choiceList/></ui><items><text>One</text><text>Two</text></items>"
        "<items save=\"1\"><text>one</text><text>two</text></items><value><text>one</text></value></field>");
    g_test_message ("Opening choice with keyboard");
    GtkWidget *combo = editing_open (&f, GTK_TYPE_COMBO_BOX);
    graphene_rect_t bounds;
    g_assert_true (gtk_widget_compute_bounds (combo, f.window, &bounds));
    Display *display = gdk_x11_display_get_xdisplay (gdk_display_get_default ());
    GdkSurface *surface = gtk_native_get_surface (GTK_NATIVE (f.window));
    Window child;
    int x, y;
    g_assert_true (translate (display, gdk_x11_surface_get_xid (surface), DefaultRootWindow (display),
                             bounds.origin.x + bounds.size.width / 2,
                             bounds.origin.y + bounds.size.height / 2, &x, &y, &child));
    gtk_combo_box_popdown (GTK_COMBO_BOX (combo));
    spin_editing ();
    for (int i = 0; i < 3; ++i) {
        g_test_message ("Held mouse click %d at %d,%d", i, x, y);
        motion (display, -1, x, y, 0);
        flush (display);
        spin_editing ();
        button (display, 1, True, 0);
        flush (display);
        spin_editing ();
        g_assert_null (find_widget_type (f.view, GTK_TYPE_COMBO_BOX));
        button (display, 1, False, 0);
        flush (display);
        spin_editing ();
        combo = find_widget_type (f.view, GTK_TYPE_COMBO_BOX);
        g_assert_nonnull (combo);
        gboolean shown = FALSE;
        g_object_get (combo, "popup-shown", &shown, NULL);
        g_assert_true (shown);
        unsigned int code = keycode (display, i == 1 ? XK_Up : XK_Down);
        key (display, code, True, 0);
        key (display, code, False, 0);
        code = keycode (display, XK_Return);
        key (display, code, True, 0);
        key (display, code, False, 0);
        flush (display);
        spin_editing ();
        editing_assert_choice (&f, i == 1 ? 0 : 1);
    }
    /* Releasing away from the field cancels activation. */
    motion (display, -1, x, y, 0);
    button (display, 1, True, 0);
    flush (display);
    spin_editing ();
    motion (display, -1, x, y + 120, 0);
    button (display, 1, False, 0);
    flush (display);
    spin_editing ();
    g_assert_null (find_widget_type (f.view, GTK_TYPE_COMBO_BOX));
    editing_assert_choice (&f, 1);
    editing_free (&f);
    g_module_close (xtst);
    g_module_close (x11);
#else
    g_test_skip ("GTK was built without X11 support");
#endif
}

static void test_multiline_limit (void)
{
    EditingFixture f = editing_fixture (
        "<field name=\"name\" w=\"3in\" h=\"0.8in\"><ui><textEdit multiLine=\"1\"/></ui>"
        "<assist><toolTip>name</toolTip></assist><value><text maxChars=\"5\"/></value></field>");
    GtkWidget *editor = editing_open (&f, GTK_TYPE_TEXT_VIEW);
    GtkTextBuffer *buffer = gtk_text_view_get_buffer (GTK_TEXT_VIEW (editor));
    GtkTextIter end;
    gtk_text_buffer_get_end_iter (buffer, &end);
    gtk_text_buffer_insert (buffer, &end, "abé中文f", -1);
    g_assert_cmpint (gtk_text_buffer_get_char_count (buffer), ==, 5);
    gchar *shown = text_view_text (editor);
    g_assert_cmpstr (shown, ==, "abé中文");
    g_free (shown);
    gtk_widget_grab_focus (f.button);
    spin_editing ();
    editing_assert_value (&f, "name", "abé中文");
    editing_free (&f);
}

static void test_editable_choice (gconstpointer data)
{
    gboolean activate = GPOINTER_TO_INT (data);
    EditingFixture f = editing_fixture (
        "<field name=\"country\" w=\"3in\" h=\"0.4in\"><ui><choiceList textEntry=\"1\"/></ui>"
        "<assist><toolTip>country</toolTip></assist><value><text>ALPHA</text></value>"
        "<items><text>ALPHA</text><text>BETA</text></items></field>");
    GtkWidget *combo = editing_open (&f, GTK_TYPE_COMBO_BOX);
    GtkWidget *entry = gtk_combo_box_get_child (GTK_COMBO_BOX (combo));
    gtk_editable_set_text (GTK_EDITABLE (entry), "Custom");
    if (activate)
        g_signal_emit_by_name (entry, "activate");
    else
        gtk_widget_grab_focus (f.button);
    spin_editing ();
    editing_assert_value (&f, "country", "Custom");
    if (!activate) {
        gtk_widget_grab_focus (entry);
        gtk_editable_set_text (GTK_EDITABLE (entry), "custom");
        gtk_widget_grab_focus (f.button);
        spin_editing ();
        editing_assert_value (&f, "country", "custom");
    }
    editing_free (&f);
}

static void test_fast_field_transition (void)
{
    EditingFixture f = editing_fixture (
        "<field name=\"a\" w=\"3in\" h=\"0.4in\"><ui><textEdit/></ui>"
        "<assist><toolTip>a</toolTip></assist><value><text>first</text></value>"
        "<event activity=\"exit\"><script contentType=\"application/x-javascript\">"
        "out.rawValue=this.rawValue;</script></event></field>"
        "<field name=\"b\" w=\"3in\" h=\"0.4in\"><ui><textEdit/></ui>"
        "<assist><toolTip>b</toolTip></assist><value><text>second</text></value></field>"
        "<field name=\"out\" w=\"3in\" h=\"0.4in\" access=\"nonInteractive\"><ui><textEdit/></ui></field>");
    GtkWidget *a = editing_open (&f, GTK_TYPE_ENTRY);
    gtk_editable_set_text (GTK_EDITABLE (a), "Alice");
    gtk_widget_child_focus (f.view, GTK_DIR_TAB_FORWARD);
    GtkWidget *b = find_entry (f.view);
    g_assert_nonnull (b);
    g_assert_cmpstr (gtk_editable_get_text (GTK_EDITABLE (b)), ==, "second");
    gtk_editable_set_text (GTK_EDITABLE (b), "Bob");
    gtk_widget_grab_focus (f.button);
    spin_editing ();
    editing_assert_value (&f, "a", "Alice");
    editing_assert_value (&f, "b", "Bob");
    editing_free (&f);
}

static void test_commit_active_editor (gconstpointer data)
{
    gboolean pending = GPOINTER_TO_INT (data);
    EditingFixture f = editing_fixture (
        "<field name=\"name\" w=\"3in\" h=\"0.4in\"><ui><textEdit/></ui>"
        "<assist><toolTip>name</toolTip></assist><value><text>before</text></value>"
        "<event activity=\"exit\"><script contentType=\"application/x-javascript\">"
        "out.rawValue=this.rawValue;</script></event></field>"
        "<field name=\"out\" w=\"3in\" h=\"0.4in\" access=\"nonInteractive\"><ui><textEdit/></ui></field>");
    GtkWidget *editor = editing_open (&f, GTK_TYPE_ENTRY);
    gtk_editable_set_text (GTK_EDITABLE (editor), "Still editing");
    if (pending)
        gtk_widget_child_focus (f.view, GTK_DIR_TAB_FORWARD);
    ev_view_commit_form_fields (EV_VIEW (f.view));
    EvDocument *doc = ev_document_model_get_document (f.model);
    g_assert_true (ev_document_forms_document_is_modified (EV_DOCUMENT_FORMS (doc)));
    editing_assert_value (&f, "name", "Still editing");
    EvPage *page = ev_document_get_page (doc, 0);
    gchar *text = ev_document_text_get_text (EV_DOCUMENT_TEXT (doc), page);
    g_assert_nonnull (strstr (text, "Still editing"));
    g_free (text);
    g_object_unref (page);
    GError *error = NULL;
    g_assert_true (ev_document_save (doc, f.uri, &error));
    g_assert_no_error (error);
    EvDocument *reopened = ev_document_factory_get_document (f.uri, &error);
    g_assert_no_error (error);
    EvFormField *field = find_field (reopened, "name");
    text = ev_document_forms_form_field_text_get_text (EV_DOCUMENT_FORMS (reopened), field);
    g_assert_cmpstr (text, ==, "Still editing");
    g_free (text);
    g_object_unref (field);
    g_object_unref (reopened);
    editing_free (&f);
}

static void test_unicode_edit (void)
{
    EditingFixture f = editing_fixture (
        "<field name=\"name\" w=\"4in\" h=\"0.8in\"><ui><textEdit multiLine=\"1\"/></ui>"
        "<assist><toolTip>name</toolTip></assist></field>");
    GtkWidget *editor = editing_open (&f, GTK_TYPE_TEXT_VIEW);
    EvDocument *original = g_object_ref (ev_document_model_get_document (f.model));
    gtk_text_buffer_set_text (gtk_text_view_get_buffer (GTK_TEXT_VIEW (editor)), "Łukasz Иван 中文", -1);
    gtk_widget_grab_focus (f.button);
    spin_editing ();
    editing_assert_value (&f, "name", "Łukasz Иван 中文");
    EvDocument *doc = ev_document_model_get_document (f.model);
    g_assert_true (doc != original);
    g_object_unref (original);
    GError *error = NULL;
    g_assert_true (ev_document_save (doc, f.uri, &error));
    g_assert_no_error (error);
    /* EvDocumentText excludes annotations; pdftotext includes their
     * appearances, which must embed the fonts for the entered name. */
    gchar *argv[] = { "pdftotext", f.path, "-", NULL };
    gchar *text = NULL;
    gint status;
    g_assert_true (g_spawn_sync (NULL, argv, NULL, G_SPAWN_SEARCH_PATH, NULL, NULL,
                                &text, NULL, &status, &error));
    g_assert_no_error (error);
    g_assert_cmpint (status, ==, 0);
    g_assert_nonnull (strstr (text, "Łukasz"));
    g_assert_nonnull (strstr (text, "Иван"));
    g_assert_nonnull (strstr (text, "中文"));
    g_free (text);
    editing_free (&f);
}

int main (int argc, char **argv)
{
    g_test_init (&argc, &argv, NULL);
    gtk_init ();
    g_assert_true (ev_init ());
    g_test_add_func ("/view/xfa-dialogs", test_dialogs);
    g_test_add_data_func ("/view/editor-document-change", GINT_TO_POINTER (FALSE), test_editor_document_change);
    g_test_add_data_func ("/view/commit-document-change", GINT_TO_POINTER (TRUE), test_editor_document_change);
    g_test_add_func ("/view/launch-url", test_launch_url);
    g_test_add_data_func ("/view/tab-refresh", GINT_TO_POINTER (FALSE), test_tab_refresh);
    g_test_add_data_func ("/view/multiline-tab-refresh", GINT_TO_POINTER (TRUE), test_tab_refresh);
    g_test_add_func ("/view/ctrl-wheel-zoom", test_ctrl_wheel_zoom);
    g_test_add_func ("/view/multiline-editor", test_multiline_editor);
    g_test_add_func ("/view/multiline-limit", test_multiline_limit);
    g_test_add_data_func ("/view/editable-choice-blur", GINT_TO_POINTER (FALSE), test_editable_choice);
    g_test_add_data_func ("/view/editable-choice-enter", GINT_TO_POINTER (TRUE), test_editable_choice);
    g_test_add_func ("/view/fast-field-transition", test_fast_field_transition);
    g_test_add_data_func ("/view/commit-active-editor", GINT_TO_POINTER (FALSE), test_commit_active_editor);
    g_test_add_data_func ("/view/commit-pending-editor", GINT_TO_POINTER (TRUE), test_commit_active_editor);
    g_test_add_func ("/view/unicode-edit", test_unicode_edit);
    g_test_add_func ("/view/mouse-choice", test_mouse_choice);
    int result = g_test_run ();
    ev_shutdown ();
    return result;
}
