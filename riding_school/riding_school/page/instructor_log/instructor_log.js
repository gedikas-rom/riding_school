frappe.pages["instructor-log"].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Reitlehrer Logbuch",
        single_column: true
    });

    // Filter-Bereich
    $(page.body).append(`
        <div class="container mt-4">
            <div class="card mb-4">
                <div class="card-body">
                    <div class="row mb-3">
                        <div class="col-md-4" id="instructor-filter"></div>
                        <div class="col-md-4" id="rider-filter"></div>
                    </div>
                    <div class="row">
                        <div class="col-md-4" id="date-from-filter"></div>
                        <div class="col-md-4" id="date-to-filter"></div>
                        <div class="col-md-4 mt-4">
                            <button class="btn btn-primary btn-sm w-100" id="load-btn">Laden</button>
                        </div>
                    </div>
                </div>
            </div>
            <div id="log-list"></div>
        </div>
    `);

    // Instructor Filter
    let instructor_field = frappe.ui.form.make_control({
        parent: $("#instructor-filter"),
        df: {
            label: "Reitlehrer",
            fieldtype: "Link",
            fieldname: "instructor",
            options: "RS Instructor"
        },
        render_input: true
    });
    instructor_field.refresh();

    // Aktuellen Reitlehrer vorauswählen
    frappe.db.get_value("RS Instructor", {"user": frappe.session.user}, "name")
        .then(r => {
            if (r.message && r.message.name) {
                instructor_field.set_value(r.message.name);
            }
        });

    // Reitschüler Filter
    let rider_field = frappe.ui.form.make_control({
        parent: $("#rider-filter"),
        df: {
            label: "Reitschüler (optional)",
            fieldtype: "Link",
            fieldname: "rider",
            options: "RS Rider"
        },
        render_input: true
    });
    rider_field.refresh();

    // Datum Von
    let date_from = frappe.ui.form.make_control({
        parent: $("#date-from-filter"),
        df: {
            label: "Von",
            fieldtype: "Date",
            fieldname: "date_from",
            default: frappe.datetime.add_days(frappe.datetime.get_today(), -30)
        },
        render_input: true
    });
    date_from.refresh();
    date_from.set_value(frappe.datetime.add_days(frappe.datetime.get_today(), -30));

    // Datum Bis
    let date_to = frappe.ui.form.make_control({
        parent: $("#date-to-filter"),
        df: {
            label: "Bis",
            fieldtype: "Date",
            fieldname: "date_to",
            default: frappe.datetime.get_today()
        },
        render_input: true
    });
    date_to.refresh();
    date_to.set_value(frappe.datetime.get_today());

    function load_logs() {
        const instructor = instructor_field.get_value();
        const from = date_from.get_value();
        const to = date_to.get_value();

        if (!instructor) {
            frappe.msgprint("Bitte Reitlehrer auswählen.");
            return;
        }

        $("#log-list").html(`<div class="text-muted text-center mt-4">Wird geladen…</div>`);

        const rider = rider_field.get_value();
        frappe.call({
            method: "riding_school.riding_school.api.instructor.get_instructor_log_list",
            args: { instructor: instructor, date_from: from, date_to: to, rider: rider || null },
            callback: function(r) {
                if (!r.message || !r.message.length) {
                    $("#log-list").html(`<div class="text-muted text-center mt-4">Keine Stunden in diesem Zeitraum.</div>`);
                    return;
                }
                render_logs(r.message);
            }
        });
    }

    function render_logs(slots) {
        let html = '';
        slots.forEach(function(s) {
            const has_log = s.logbook_entry && s.logbook_entry.trim();
            const participants_html = s.participants.map(function(p) {
                const has_p_log = p.logbook_entry && p.logbook_entry.trim();
                return `
                    <div class="mb-3 p-3 border rounded" style="background:#f9f9f9">
                        <div class="mb-2">
                            <b>👤 ${p.rider_name || '–'}</b>
                            ${p.horse_name ? ' · 🐴 ' + p.horse_name : ''}
                        </div>
                        <textarea class="form-control participant-log" 
                            data-slot="${s.name}" data-rider="${p.rider_id}"
                            rows="2" placeholder="Kommentar für ${p.rider_name || 'Reitschüler'}…"
                            style="font-size:0.85rem">${p.logbook_entry || ''}</textarea>
                    </div>`;
            }).join('');

            html += `
                <div class="card mb-3">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <div>
                            <b>${frappe.datetime.str_to_user(s.slot_date)}</b>
                            &nbsp;${s.start_time.slice(0,5)} – ${s.end_time.slice(0,5)} Uhr
                            &nbsp;<span class="badge badge-${s.status === 'Completed' ? 'success' : 'info'}">${s.status}</span>
                        </div>
                        <div class="text-muted small">
                            ${s.facility_name ? '📍 ' + s.facility_name : ''}
                        </div>
                    </div>
                    <div class="card-body">
                        ${s.participants.length > 1 ? participants_html : `
                            <div class="mb-2 text-muted small">
                                ${s.participants.length === 1 ? '👤 ' + (s.participants[0].rider_name || '') + (s.participants[0].horse_name ? ' · 🐴 ' + s.participants[0].horse_name : '') : 'Kein Reitschüler'}
                            </div>
                            <textarea class="form-control slot-log" data-slot="${s.name}"
                                rows="3" placeholder="Kommentar zur Stunde…">${s.logbook_entry || ''}</textarea>
                        `}
                        <div class="mt-2 text-right">
                            <button class="btn btn-sm btn-primary save-log" data-slot="${s.name}">
                                Speichern
                            </button>
                        </div>
                    </div>
                </div>`;
        });

        $("#log-list").html(html);

        // Save Buttons
        $(".save-log").on("click", function() {
            const slot_name = $(this).data("slot");
            const card = $(this).closest(".card-body");

            // Einzelstunde oder Slot-Log
            const slot_textarea = card.find(".slot-log[data-slot='" + slot_name + "']");
            if (slot_textarea.length) {
                save_slot_log(slot_name, null, slot_textarea.val());
            }

            // Teilnehmer-Logs
            card.find(".participant-log").each(function() {
                const rider_id = $(this).data("rider");
                save_slot_log(slot_name, rider_id, $(this).val());
            });
        });
    }

    function save_slot_log(slot_name, rider_id, entry) {
        frappe.call({
            method: "riding_school.riding_school.api.instructor.save_logbook_entry",
            args: {
                slot_name: slot_name,
                entry: entry,
                rider_id: rider_id || null
            },
            callback: function(r) {
                frappe.show_alert({ message: "Gespeichert", indicator: "green" });
            }
        });
    }

    $("#load-btn").on("click", load_logs);
    load_logs();
};
