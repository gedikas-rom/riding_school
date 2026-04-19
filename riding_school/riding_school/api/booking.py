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
            "instructor", "facility", "status",
            "skill_level", "slot_type", "max_participants"
        ]
        # slot_type wird direkt mitgeladen
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

        # Gewichtslimit wird bei Buchung geprüft

        is_my_booking = slot.name in my_bookings

        # Teilnehmer-Count für Gruppenslots
        max_p = frappe.db.get_value("RS Lesson Slot", slot.name, "max_participants") or 1
        current_p = frappe.db.count("RS Slot Participant", {"parent": slot.name})
        is_full = current_p >= max_p

        # Nur Released anzeigen (außer eigene Buchungen und abgeschlossene)
        if slot.status in ["Booked", "Completed"] and not is_my_booking:
            continue

        # Volle Gruppenslots ausblenden (außer eigene Buchungen)
        if is_full and not is_my_booking and slot.status == "Released":
            continue

        instructor_name = frappe.db.get_value("RS Instructor", slot.instructor, "full_name") if slot.instructor else None
        # Pferde aus Teilnehmern holen
        participant_horses = frappe.db.get_all(
            "RS Slot Participant",
            filters={"parent": slot.name},
            fields=["horse"]
        )
        horse_names = [
            frappe.db.get_value("RS Horse", p.horse, "horse_name")
            for p in participant_horses if p.horse
        ]
        horse_name = ", ".join(filter(None, horse_names)) or None
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
            "booking_name": booking_name,
            "max_participants": max_p,
            "current_participants": current_p,
            "is_group": max_p > 1,
            "slot_type": slot.slot_type or "Einzelstunde"
        })

    return sorted(result, key=lambda x: (str(x["slot_date"]), str(x["start_time"])), reverse=True)


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

    # Platz verfügbar?
    max_p = slot.max_participants or 1
    current_p = frappe.db.count("RS Slot Participant", {"parent": slot_name})
    if current_p >= max_p:
        return {"success": False, "error": "Dieser Slot ist bereits voll belegt"}

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

    # Passendes freies Pferd finden
    rider_doc = frappe.get_doc("RS Rider", rider)
    assigned_horse = None

    # Bereits belegte Pferde in diesem Slot
    taken_horses = frappe.db.get_all(
        "RS Slot Participant",
        filters={"parent": slot_name},
        pluck="horse"
    )

    # Bevorzugte Pferde des Reitschülers prüfen
    preferred = getattr(rider_doc, 'preferred_horses', None) or []
    excluded_raw = getattr(rider_doc, 'excluded_horses', None) or []
    excluded = [e.horse for e in excluded_raw if e and e.horse]

    # Verfügbare Pferde suchen
    available_horses = frappe.get_all(
        "RS Horse",
        filters={"status": "Active"},
        fields=["name", "horse_name", "max_weight_kg"]
    )

    for horse in available_horses:
        if horse.name in taken_horses:
            continue
        if horse.name in excluded:
            continue
        if horse.max_weight_kg and rider_doc.weight_kg and rider_doc.weight_kg > horse.max_weight_kg:
            continue
        assigned_horse = horse.name
        break

    # Reitschüler als Teilnehmer eintragen
    slot.reload()
    slot.append("participants", {
        "rider": rider,
        "horse": assigned_horse,
        "confirmed": 1
    })

    # Slot-Status anpassen
    new_count = current_p + 1
    if new_count >= max_p:
        slot.status = "Booked"

    slot.save(ignore_permissions=True)

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

    frappe.db.commit()
    return {
        "success": True,
        "booking": booking.name,
        "horse": assigned_horse,
        "message": f"Buchung erfolgreich!" + (f" Pferd: {frappe.db.get_value('RS Horse', assigned_horse, 'horse_name')}" if assigned_horse else " Kein Pferd verfügbar – Backoffice wird zuweisen.")
    }


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


@frappe.whitelist()
def get_rider_diary():
    """Gibt alle vergangenen Stunden des Reitschülers zurück"""
    if frappe.session.user == "Guest":
        return []

    rider = frappe.db.get_value("RS Rider", {"user": frappe.session.user}, "name")
    if not rider:
        return []

    bookings = frappe.get_all(
        "RS Booking",
        filters={"rider": rider, "status": ["in", ["Completed", "Reserved"]]},
        fields=["name", "lesson_slot", "billing_type"],
        limit=100
    )

    # Nach Slot-Datum sortieren (neueste zuerst)
    result_unsorted = []

    result = []
    for b in bookings:
        slot = frappe.get_doc("RS Lesson Slot", b.lesson_slot)
        # Nur abgeschlossene oder gebuchte Slots anzeigen
        if slot.status not in ["Completed", "Booked", "Released"]:
            continue
        instructor_name = frappe.db.get_value("RS Instructor", slot.instructor, "full_name") if slot.instructor else None
        # Pferde aus Teilnehmern holen
        participant_horses = frappe.db.get_all(
            "RS Slot Participant",
            filters={"parent": slot.name},
            fields=["horse"]
        )
        horse_names = [
            frappe.db.get_value("RS Horse", p.horse, "horse_name")
            for p in participant_horses if p.horse
        ]
        horse_name = ", ".join(filter(None, horse_names)) or None
        facility_name = frappe.db.get_value("RS Facility", slot.facility, "facility_name") if slot.facility else None

        # Rider Log laden
        log = frappe.db.get_value(
            "RS Rider Log",
            {"rider": rider, "lesson_slot": b.lesson_slot},
            ["name", "lesson_rating", "instructor_rating", "rider_comment"],
            as_dict=True
        )

        # Logbucheintrag: bei Gruppenslots aus Teilnehmer-Eintrag
        if len(slot.participants) > 1:
            instructor_comment = frappe.db.get_value(
                "RS Slot Participant",
                {"parent": slot.name, "rider": rider},
                "logbook_entry"
            ) or ""
        else:
            instructor_comment = slot.logbook_entry or ""

        result.append({
            "booking": b.name,
            "slot": slot.name,
            "slot_date": str(slot.slot_date),
            "start_time": str(slot.start_time),
            "end_time": str(slot.end_time),
            "instructor_name": instructor_name,
            "horse_name": horse_name,
            "facility_name": facility_name,
            "instructor_comment": instructor_comment,
            "log_name": log.name if log else None,
            "lesson_rating": round((log.lesson_rating or 0) * 5) if log else 0,
            "instructor_rating": round((log.instructor_rating or 0) * 5) if log else 0,
            "rider_comment": log.rider_comment if log else ""
        })

    return sorted(result, key=lambda x: (x["slot_date"], x["start_time"]), reverse=True)


@frappe.whitelist()
def save_rider_log(lesson_slot, lesson_rating, instructor_rating, rider_comment):
    """Speichert oder aktualisiert einen Tagebucheintrag"""
    if frappe.session.user == "Guest":
        return {"success": False}

    rider = frappe.db.get_value("RS Rider", {"user": frappe.session.user}, "name")
    if not rider:
        return {"success": False, "error": "Kein Reitschüler-Profil"}

    slot = frappe.get_doc("RS Lesson Slot", lesson_slot)

    existing = frappe.db.get_value(
        "RS Rider Log",
        {"rider": rider, "lesson_slot": lesson_slot},
        "name"
    )

    if existing:
        log = frappe.get_doc("RS Rider Log", existing)
        log.lesson_rating = int(lesson_rating) / 5
        log.instructor_rating = int(instructor_rating) / 5
        log.rider_comment = rider_comment
        log.save(ignore_permissions=True)
    else:
        log = frappe.get_doc({
            "doctype": "RS Rider Log",
            "rider": rider,
            "lesson_slot": lesson_slot,
            "log_date": slot.slot_date,
            "lesson_rating": int(lesson_rating) / 5,
            "instructor_rating": int(instructor_rating) / 5,
            "rider_comment": rider_comment
        })
        log.insert(ignore_permissions=True)

    frappe.db.commit()
    return {"success": True}
