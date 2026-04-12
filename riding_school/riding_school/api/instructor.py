import frappe
from frappe import _


@frappe.whitelist()
def get_instructor_slots(date):
    """Gibt die Slots des eingeloggten Reitlehrers für einen Tag zurück"""
    if frappe.session.user == "Guest":
        frappe.throw(_("Nicht eingeloggt"))

    instructor = frappe.db.get_value(
        "RS Instructor",
        {"user": frappe.session.user},
        "name"
    )

    if not instructor:
        return []

    slots = frappe.get_all(
        "RS Lesson Slot",
        filters={
            "instructor": instructor,
            "slot_date": date,
            "status": ["!=", "Cancelled"]
        },
        fields=["name", "start_time", "end_time", "status", "horse",
                "facility", "logbook_entry", "slot_type"]
    )

    result = []
    for slot in slots:
        # Reitschüler aus Buchung holen
        booking = frappe.db.get_value(
            "RS Booking",
            {"lesson_slot": slot.name, "status": ["!=", "Cancelled"]},
            ["rider"],
            as_dict=True
        )
        rider_name = None
        if booking:
            rider_name = frappe.db.get_value("RS Rider", booking.rider, "full_name")

        result.append({
            "name": slot.name,
            "start_time": str(slot.start_time),
            "end_time": str(slot.end_time),
            "status": slot.status,
            "horse_name": frappe.db.get_value("RS Horse", slot.horse, "horse_name") if slot.horse else None,
            "facility_name": frappe.db.get_value("RS Facility", slot.facility, "facility_name") if slot.facility else None,
            "rider_name": rider_name,
            "logbook_entry": slot.logbook_entry or ""
        })

    # Korrekte Zeitsortiering (HH:MM:SS als String)
    return sorted(result, key=lambda x: str(x["start_time"]))


@frappe.whitelist()
def save_logbook_entry(slot_name, entry):
    """Speichert einen Logbuch-Eintrag für einen Slot"""
    if frappe.session.user == "Guest":
        frappe.throw(_("Nicht eingeloggt"))

    instructor = frappe.db.get_value(
        "RS Instructor",
        {"user": frappe.session.user},
        "name"
    )

    slot = frappe.get_doc("RS Lesson Slot", slot_name)

    if slot.instructor != instructor:
        frappe.throw(_("Keine Berechtigung"))

    slot.logbook_entry = entry
    slot.save(ignore_permissions=True)
    frappe.db.commit()

    return {"success": True}
