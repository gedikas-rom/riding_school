frappe.ui.form.on('RS Lesson Slot', {
    refresh: function(frm) {

        // Status-Farben
        const status_colors = {
            'Open': 'orange',
            'Planned': 'blue',
            'Released': 'green',
            'Booked': 'purple',
            'Completed': 'gray',
            'Cancelled': 'red'
        };
        if (frm.doc.status) {
            frm.page.set_indicator(
                frm.doc.status,
                status_colors[frm.doc.status] || 'gray'
            );
        }

        if (frm.is_new()) return;

        // Open → Planned
        if (frm.doc.status === 'Open') {
            frm.add_custom_button(__('Einplanen'), function() {
                let missing = [];
                if (!frm.doc.facility) missing.push('Reitplatz');

                let do_plan = function() {
                    frappe.call({
                        method: 'riding_school.riding_school.api.slot_generator.set_slot_status',
                        args: { slot_name: frm.doc.name, status: 'Planned' },
                        callback: function(r) {
                            frm.reload_doc();
                            frappe.show_alert({ message: __('Slot eingeplant'), indicator: 'blue' });
                        }
                    });
                };

                if (missing.length > 0) {
                    let msg = __('Folgende Felder fehlen noch: <b>{0}</b><br><br>Trotzdem einplanen?',
                        [missing.join(', ')]);
                    frappe.confirm(msg, do_plan);
                } else {
                    frappe.confirm(__('Slot einplanen?'), do_plan);
                }
            }, __('Aktionen')).addClass('btn-primary');
        }

        // Planned → Released
        if (frm.doc.status === 'Planned') {
            frm.add_custom_button(__('Freigeben'), function() {
                let missing = [];
                if (!frm.doc.instructor) missing.push('Reitlehrer');
                if (!frm.doc.facility) missing.push('Reitplatz');

                if (missing.length > 0) {
                    let msg = __('Folgende Felder fehlen noch: <b>{0}</b><br><br>Trotzdem freigeben?',
                        [missing.join(', ')]);
                    frappe.confirm(msg, function() {
                        release_slot(frm);
                    });
                } else {
                    frappe.confirm(__('Slot für Reitschüler freigeben?'), function() {
                        release_slot(frm);
                    });
                }
            }, __('Aktionen')).addClass('btn-primary');
        }

        // Released → Planned
        if (frm.doc.status === 'Released') {
            frm.add_custom_button(__('Zurück zu Geplant'), function() {
                frappe.confirm(__('Slot zurück auf Geplant setzen?'), function() {
                    frappe.call({
                        method: 'riding_school.riding_school.api.slot_generator.set_slot_status',
                        args: { slot_name: frm.doc.name, status: 'Planned' },
                        callback: function(r) {
                            frm.reload_doc();
                            frappe.show_alert({ message: __('Slot zurück auf Geplant'), indicator: 'blue' });
                        }
                    });
                });
            }, __('Aktionen'));
        }

        // Planned → Open
        if (frm.doc.status === 'Planned') {
            frm.add_custom_button(__('Zurück zu Offen'), function() {
                frappe.confirm(__('Slot zurück auf Offen setzen?'), function() {
                    frappe.call({
                        method: 'riding_school.riding_school.api.slot_generator.set_slot_status',
                        args: { slot_name: frm.doc.name, status: 'Open' },
                        callback: function(r) {
                            frm.reload_doc();
                            frappe.show_alert({ message: __('Slot zurück auf Offen'), indicator: 'orange' });
                        }
                    });
                });
            }, __('Aktionen'));
        }

        // Released → Open
        if (frm.doc.status === 'Released') {
            frm.add_custom_button(__('Zurück zu Offen'), function() {
                frappe.confirm(__('Slot zurück auf Offen setzen?'), function() {
                    frappe.call({
                        method: 'riding_school.riding_school.api.slot_generator.set_slot_status',
                        args: { slot_name: frm.doc.name, status: 'Open' },
                        callback: function(r) {
                            frm.reload_doc();
                            frappe.show_alert({ message: __('Slot zurück auf Offen'), indicator: 'orange' });
                        }
                    });
                });
            }, __('Aktionen'));
        }

        // Open/Planned/Released → Cancelled
        if (['Open', 'Planned', 'Released'].includes(frm.doc.status)) {
            frm.add_custom_button(__('Stornieren'), function() {
                frappe.confirm(__('Slot wirklich stornieren?'), function() {
                    frappe.call({
                        method: 'riding_school.riding_school.api.slot_generator.set_slot_status',
                        args: { slot_name: frm.doc.name, status: 'Cancelled' },
                        callback: function(r) {
                            frm.reload_doc();
                            frappe.show_alert({ message: __('Slot storniert'), indicator: 'red' });
                        }
                    });
                });
            }, __('Aktionen'));
        }

        // Booked → Completed (Reitlehrer nach Stunde)
        if (frm.doc.status === 'Booked') {
            frm.add_custom_button(__('Stunde abschließen'), function() {
                frappe.confirm(__('Reitstunde als abgeschlossen markieren?'), function() {
                    frappe.call({
                        method: 'riding_school.riding_school.api.slot_generator.set_slot_status',
                        args: { slot_name: frm.doc.name, status: 'Completed' },
                        callback: function(r) {
                            frm.reload_doc();
                            frappe.show_alert({ message: __('Stunde abgeschlossen'), indicator: 'green' });
                        }
                    });
                });
            }, __('Aktionen')).addClass('btn-primary');

            frm.add_custom_button(__('Stornieren'), function() {
                frappe.confirm(__('Buchung stornieren? Der Reitschüler wird informiert.'), function() {
                    frappe.call({
                        method: 'riding_school.riding_school.api.slot_generator.set_slot_status',
                        args: { slot_name: frm.doc.name, status: 'Cancelled' },
                        callback: function(r) {
                            frm.reload_doc();
                            frappe.show_alert({ message: __('Buchung storniert'), indicator: 'red' });
                        }
                    });
                });
            }, __('Aktionen'));
        }
    }
});

function release_slot(frm) {
    frappe.call({
        method: 'riding_school.riding_school.api.slot_generator.set_slot_status',
        args: { slot_name: frm.doc.name, status: 'Released' },
        callback: function(r) {
            frm.reload_doc();
            frappe.show_alert({ message: __('Slot freigegeben'), indicator: 'green' });
        }
    });
}

// Tagebuch Aktionen
frappe.ui.form.on('RS Lesson Slot', {
    refresh: function(frm) {
        if (frm.is_new() || frm.doc.status !== 'Completed') return;

        frm.add_custom_button(__('Tagebucheinträge'), function() {
            frappe.set_route('List', 'RS Rider Log', {lesson_slot: frm.doc.name});
        }, __('Tagebuch'));

        frm.add_custom_button(__('Neuer Eintrag'), function() {
            frappe.new_doc('RS Rider Log', {
                lesson_slot: frm.doc.name,
                log_date: frm.doc.slot_date
            });
        }, __('Tagebuch'));
    }
});
