frappe.ui.form.on('RS Horse', {
    refresh: function(frm) {
        if (frm.is_new()) return;

        frm.add_custom_button(__('Notiz hinzufügen'), function() {
            let d = new frappe.ui.Dialog({
                title: 'Neue Notiz für ' + frm.doc.horse_name,
                fields: [
                    {
                        fieldname: 'category',
                        fieldtype: 'Select',
                        label: 'Kategorie',
                        options: 'Schmied\nTierarzt\nSonstiges',
                        reqd: 1
                    },
                    {
                        fieldname: 'note_date',
                        fieldtype: 'Date',
                        label: 'Datum',
                        reqd: 1,
                        default: frappe.datetime.get_today()
                    },
                    {
                        fieldname: 'note_time',
                        fieldtype: 'Time',
                        label: 'Uhrzeit'
                    },
                    {
                        fieldname: 'duration_minutes',
                        fieldtype: 'Int',
                        label: 'Dauer (Minuten)'
                    },
                    {
                        fieldname: 'note',
                        fieldtype: 'Text',
                        label: 'Notiz',
                        reqd: 1
                    }
                ],
                primary_action_label: 'Speichern',
                primary_action: function(values) {
                    frappe.call({
                        method: 'frappe.client.insert',
                        args: {
                            doc: {
                                doctype: 'RS Horse Note',
                                horse: frm.doc.name,
                                category: values.category,
                                note_date: values.note_date,
                                note_time: values.note_time,
                                duration_minutes: values.duration_minutes,
                                note: values.note
                            }
                        },
                        callback: function(r) {
                            d.hide();
                            frappe.show_alert({
                                message: 'Notiz gespeichert',
                                indicator: 'green'
                            });
                        }
                    });
                }
            });
            d.show();
        }, __('Aktionen'));

        frm.add_custom_button(__('Alle Notizen'), function() {
            frappe.set_route('List', 'RS Horse Note', {horse: frm.doc.name});
        }, __('Aktionen'));
    }
});
