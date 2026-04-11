import frappe
from frappe import _


@frappe.whitelist()
def get_available_slots(start, end):
    """Gibt verfügbare Slots für den eingeloggten Reitschüler zurück"""
    if frappe.session.user == "Guest":
        frappe.throw(_("Nicht eingeloggt"))

    # Rider laden
    rider = frappe.db.get_value(
        "RS Rider",
        {"user": frappe.session.user},
        ["name", "skill_level", "weight_kg"],
        as_dict=True
    )

    # Released Slots laden
    filters = {
        "slot_date": ["between", [start, end]],
        "status": ["in", ["Released", "Booked", "Completed"]]
    }

    slots = frappe.get_all(
        "RS Lesson Slot",
        filters=filters,
        fields=[
            "name", "slot_date", "start_time", "end_time",
            "instructor", "horse", "facility", "status",
            "skill_level", "slot_type"
        ]
    )

    # Meine Buchungen laden
    my_bookings = []
    if rider:
        my_bookings = frappe.get_all(
            "RS Booking",
            filters={"rider": rider.name, "status": ["!=", "Cancelled"]},
            pluck="lesson_slot"
        )

    result = []
    for slot in slots:
        # Skill Level prüfen
        if rider and slot.skill_level and rider.skill_level:
            skill_order = ["Beginner", "Intermediate", "Advanced", "Competition"]
            rider_idx = skill_order.index(rider.skill_level) if rider.skill_level in skill_order else 0
            slot_idx = skill_order.index(slot.skill_level) if slot.skill_level in skill_order else 0
            if rider_idx < slot_idx:
                continue

        # Gewichtslimit prüfen
        if rider and rider.weight_kg and slot.horse:
            max_weight = frappe.db.get_value("RS Horse", slot.horse, "max_weight_kg")
            if max_weight and rider.weight_kg > max_weight:
                continue

        is_my_booking = slot.name in my_bookings

        # Nur Released anzeigen (außer eigene Buchungen und abgeschlossene)
        if slot.status in ["Booked", "Completed"] and not is_my_booking:
            continue

        instructor_name = frappe.db.get_value("RS Instructor", slot.instructor, "full_name") if slot.instructor else None
        horse_name = frappe.db.get_value("RS Horse", slot.horse, "horse_name") if slot.horse else None
        facility_name = frappe.db.get_value("RS Facility", slot.facility, "facility_name") if slot.facility else None

        # Buchungsname für Stornierung
        booking_name = None
        if is_my_booking and rider:
            rider_name = rider.name if hasattr(rider, 'name') else rider
            booking_name = frappe.db.get_value(
                "RS Booking",
                {"lesson_slot": slot.name, "rider": rider_name, "status": ["!=", "Cancelled"]},
                "name"
            )

        result.append({
            "name": slot.name,
            "slot_date": str(slot.slot_date),
            "start_time": str(slot.start_time),
            "end_time": str(slot.end_time),
            "instructor_name": instructor_name,
            "horse_name": horse_name,
            "facility_name": facility_name,
            "status": slot.status,
            "is_my_booking": is_my_booking,
            "booking_name": booking_name
        })

    return result


@frappe.whitelist()
def get_rider_time_cards():
    """Gibt aktive Zeitkarten des eingeloggten Reitschülers zurück"""
    if frappe.session.user == "Guest":
        return []

    rider = frappe.db.get_value("RS Rider", {"user": frappe.session.user}, "name")
    if not rider:
        return []

    return frappe.get_all(
        "RS Time Card",
        filters={"rider": rider, "status": "Active"},
        fields=["name", "total_lessons", "used_lessons", "remaining_lessons", "valid_until"]
    )


@frappe.whitelist()
def book_slot(slot_name, billing_type="Single", time_card=None):
    """Bucht einen Slot für den eingeloggten Reitschüler"""
    if frappe.session.user == "Guest":
        return {"success": False, "error": "Nicht eingeloggt"}

    rider = frappe.db.get_value("RS Rider", {"user": frappe.session.user}, "name")
    if not rider:
        return {"success": False, "error": "Kein Reitschüler-Profil gefunden"}

    slot = frappe.get_doc("RS Lesson Slot", slot_name)
    if slot.status != "Released":
        return {"success": False, "error": "Dieser Slot ist nicht mehr verfügbar"}

    # Bereits gebucht?
    existing = frappe.db.exists("RS Booking", {
        "rider": rider,
        "lesson_slot": slot_name,
        "status": ["!=", "Cancelled"]
    })
    if existing:
        return {"success": False, "error": "Du hast diesen Slot bereits gebucht"}

    # Zeitkarte prüfen
    if billing_type == "Time Card":
        if not time_card:
            return {"success": False, "error": "Bitte eine Zeitkarte auswählen"}
        tc = frappe.get_doc("RS Time Card", time_card)
        if tc.status != "Active":
            return {"success": False, "error": "Diese Zeitkarte ist nicht mehr aktiv"}
        if (tc.remaining_lessons or 0) <= 0:
            return {"success": False, "error": "Diese Zeitkarte hat keine Stunden mehr"}
        if tc.rider != rider:
            return {"success": False, "error": "Diese Zeitkarte gehört nicht dir"}

    # Buchung anlegen
    booking = frappe.get_doc({
        "doctype": "RS Booking",
        "rider": rider,
        "lesson_slot": slot_name,
        "status": "Reserved",
        "billing_type": billing_type,
        "time_card": time_card if billing_type == "Time Card" else None
    })
    booking.insert(ignore_permissions=True)

    # Slot-Status auf Booked setzen
    slot.status = "Booked"
    slot.save(ignore_permissions=True)

    frappe.db.commit()
    return {"success": True, "booking": booking.name}


@frappe.whitelist()
def get_cancellation_info(booking_name):
    """Gibt Infos zur Stornierung zurück – kostenpflichtig oder nicht"""
    if frappe.session.user == "Guest":
        return {"success": False}

    booking = frappe.get_doc("RS Booking", booking_name)
    slot = frappe.get_doc("RS Lesson Slot", booking.lesson_slot)
    settings = frappe.get_single("RS Settings")
    cancellation_hours = settings.cancellation_hours or 24

    from datetime import datetime
    slot_datetime = datetime.combine(slot.slot_date,
        (datetime.min + slot.start_time).time())
    hours_until_slot = (slot_datetime - datetime.now()).total_seconds() / 3600

    is_late = hours_until_slot < cancellation_hours

    return {
        "is_late": is_late,
        "hours_until_slot": round(hours_until_slot, 1),
        "cancellation_hours": cancellation_hours,
        "late_cancellation_fee": settings.late_cancellation_fee or "Stunde wird berechnet"
    }


@frappe.whitelist()
def cancel_booking(booking_name):
    """Storniert eine Buchung des eingeloggten Reitschülers"""
    if frappe.session.user == "Guest":
        return {"success": False, "error": "Nicht eingeloggt"}

    rider = frappe.db.get_value("RS Rider", {"user": frappe.session.user}, "name")
    if not rider:
        return {"success": False, "error": "Kein Reitschüler-Profil gefunden"}

    booking = frappe.get_doc("RS Booking", booking_name)

    if booking.rider != rider:
        return {"success": False, "error": "Diese Buchung gehört nicht dir"}

    if booking.status in ["Completed", "Cancelled"]:
        return {"success": False, "error": "Diese Buchung kann nicht storniert werden"}

    # Slot laden
    slot = frappe.get_doc("RS Lesson Slot", booking.lesson_slot)

    # Stornierungsfrist prüfen
    settings = frappe.get_single("RS Settings")
    cancellation_hours = settings.cancellation_hours or 24

    from datetime import datetime, timedelta
    slot_datetime = datetime.combine(slot.slot_date, 
        (datetime.min + slot.start_time).time())
    now = datetime.now()
    hours_until_slot = (slot_datetime - now).total_seconds() / 3600

    is_late = hours_until_slot < cancellation_hours

    # Buchung stornieren
    booking.status = "Cancelled"
    booking.save(ignore_permissions=True)

    # Slot zurück auf Released
    slot.status = "Released"
    slot.save(ignore_permissions=True)

    # Zeitkarte zurückbuchen wenn rechtzeitig storniert
    if not is_late and booking.billing_type == "Time Card" and booking.time_card:
        tc = frappe.get_doc("RS Time Card", booking.time_card)
        tc.used_lessons = max(0, (tc.used_lessons or 0) - 1)
        tc.remaining_lessons = (tc.total_lessons or 0) - tc.used_lessons
        tc.status = "Active"
        tc.save(ignore_permissions=True)

    frappe.db.commit()

    if is_late:
        msg = f"Buchung storniert. Achtung: Die Stornierungsfrist von {cancellation_hours} Stunden wurde unterschritten – {settings.late_cancellation_fee}."
    else:
        msg = "Buchung erfolgreich storniert."

    return {"success": True, "message": msg, "is_late": is_late}
