frappe.pages["slot-generator"].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Slot Generator",
        single_column: true
    });

    page.add_menu_item("Slot-Konfiguration öffnen", function() {
        frappe.set_route("Form", "RS Slot Config");
    });

    frappe.call({
        method: "frappe.client.get",
        args: { doctype: "RS Slot Config", name: "RS Slot Config" },
        callback: function(r) {
            if (r.message) {
                let config = r.message;
                let days = [];
                if (config.monday) days.push("Mo");
                if (config.tuesday) days.push("Di");
                if (config.wednesday) days.push("Mi");
                if (config.thursday) days.push("Do");
                if (config.friday) days.push("Fr");
                if (config.saturday) days.push("Sa");
                if (config.sunday) days.push("So");

                $(page.body).append(`
                    <div class="container mt-4">
                        <div class="card mb-4">
                            <div class="card-body">
                                <h5>Aktuelle Konfiguration
                                    <a href="/app/rs-slot-config" class="btn btn-xs btn-default ml-2">
                                        Bearbeiten
                                    </a>
                                </h5>
                                <table class="table table-bordered mt-2">
                                    <tr>
                                        <td><b>Slot-Dauer</b></td>
                                        <td>${config.slot_duration} Minuten</td>
                                    </tr>
                                    <tr>
                                        <td><b>Aktive Tage</b></td>
                                        <td>${days.join(", ")}</td>
                                    </tr>
                                    <tr>
                                        <td><b>Pause zwischen Slots</b></td>
                                        <td>${config.break_duration || 0} Minuten</td>
                                    </tr>
                                </table>
                            </div>
                        </div>

                        <div class="card mb-4">
                            <div class="card-body">
                                <h5>Slots generieren</h5>
                                <div class="row mt-3">
                                    <div class="col-md-4">
                                        <div id="week-picker"></div>
                                    </div>
                                    <div class="col-md-4 mt-4">
                                        <button class="btn btn-primary" id="generate-btn">
                                            Slots generieren
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="card">
                            <div class="card-body">
                                <h5>Hinweise</h5>
                                <ul>
                                    <li>Bitte einen <b>Montag</b> auswählen</li>
                                    <li>Slots werden basierend auf den <b>Reitlehrer-Verfügbarkeiten</b> generiert</li>
                                    <li>Bereits gebuchte oder abgeschlossene Slots werden <b>nicht</b> gelöscht</li>
                                    <li>Nach der Generierung Pferd und Reitplatz im <b>Kalender</b> zuweisen</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                `);

                let week_input = frappe.ui.form.make_control({
                    parent: $("#week-picker"),
                    df: {
                        label: "Woche (Montag)",
                        fieldtype: "Date",
                        fieldname: "week_start"
                    },
                    render_input: true
                });
                week_input.refresh();

                function do_generate(week_start) {
                    frappe.call({
                        method: "riding_school.riding_school.api.slot_generator.generate_slots_for_week",
                        args: { week_start_date: week_start },
                        freeze: true,
                        freeze_message: "Slots werden generiert...",
                        callback: function(r) {
                            if (r.message && r.message.success) {
                                frappe.msgprint({
                                    title: "Fertig",
                                    message: r.message.message,
                                    indicator: "green"
                                });
                            }
                        }
                    });
                }

                $("#generate-btn").on("click", function() {
                    let week_start = week_input.get_value();

                    if (!week_start) {
                        frappe.msgprint("Bitte ein Datum auswählen.");
                        return;
                    }

                    let d = new Date(week_start);
                    if (d.getDay() !== 1) {
                        frappe.msgprint("Bitte einen Montag auswählen.");
                        return;
                    }

                    // Prüfen ob bereits Slots existieren
                    frappe.call({
                        method: "riding_school.riding_school.api.slot_generator.check_existing_slots",
                        args: { week_start_date: week_start },
                        callback: function(r) {
                            let count = r.message.existing_count;

                            if (count > 0) {
                                // Überschreiben-Dialog
                                let d = new frappe.ui.Dialog({
                                    title: "Vorhandene Slots gefunden",
                                    fields: [
                                        {
                                            fieldtype: "HTML",
                                            options: `<p>Es gibt bereits <b>${count} offene Slots</b> für diese Woche.</p>
                                                     <p>Sollen diese gelöscht und neu generiert werden?</p>
                                                     <p><small>Gebuchte und abgeschlossene Slots bleiben erhalten.</small></p>`
                                        }
                                    ],
                                    primary_action_label: "Löschen & neu generieren",
                                    primary_action: function() {
                                        d.hide();
                                        frappe.call({
                                            method: "riding_school.riding_school.api.slot_generator.delete_open_slots_for_week",
                                            args: { week_start_date: week_start },
                                            freeze: true,
                                            freeze_message: "Alte Slots werden gelöscht...",
                                            callback: function() {
                                                do_generate(week_start);
                                            }
                                        });
                                    },
                                    secondary_action_label: "Abbrechen"
                                });
                                d.show();
                            } else {
                                frappe.confirm(
                                    `Slots für die Woche ab <b>${week_start}</b> generieren?`,
                                    function() { do_generate(week_start); }
                                );
                            }
                        }
                    });
                });
            }
        }
    });
};
