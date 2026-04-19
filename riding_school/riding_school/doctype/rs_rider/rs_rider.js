frappe.ui.form.on('RS Rider', {
    refresh: function(frm) {
        if (frm.is_new()) return;

        frm.add_custom_button(__('Tagebuch anzeigen'), function() {
            frappe.set_route('List', 'RS Rider Log', {rider: frm.doc.name});
        }, __('Aktionen'));

        frm.add_custom_button(__('Neuer Tagebucheintrag'), function() {
            frappe.new_doc('RS Rider Log', {
                rider: frm.doc.name,
                log_date: frappe.datetime.get_today()
            });
        }, __('Aktionen'));
    }
});
