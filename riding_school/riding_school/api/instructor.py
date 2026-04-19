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

        # Teilnehmer laden inkl. Logbucheintrag direkt aus DB
        participants = frappe.db.sql("""
            SELECT rider, horse, logbook_entry
            FROM `tabRS Slot Participant`
            WHERE parent = %s
            ORDER BY idx
        """, slot.name, as_dict=True)
        rider_names = []
        rider_ids = []
        horse_names = []
        horse_ids = []
        for p in participants:
            if p.rider:
                rn = frappe.db.get_value("RS Rider", p.rider, "full_name")
                if rn:
                    rider_names.append(rn)
                    rider_ids.append(p.rider)
            if p.horse:
                hn = frappe.db.get_value("RS Horse", p.horse, "horse_name")
                if hn:
                    horse_names.append(hn)
                    horse_ids.append(p.horse)

        current_p = len(participants)
        max_p = slot.max_participants or 1
        icons = {'Einzelstunde': '🐴', 'Gruppenstunde': '👥', 'Event': '🎪'}
        slot_icon = icons.get(slot.slot_type, '🐴')

        # Teilnehmer als Array mit Logbucheintrag
        participants_list = []
        for j, p in enumerate(participants):
            participants_list.append({
                "rider_id": p.rider,
                "rider_name": rider_names[j] if j < len(rider_names) else None,
                "horse_id": p.horse,
                "horse_name": horse_names[j] if j < len(horse_names) else None,
                "logbook_entry": p.logbook_entry or ""
            })

        result.append({
            "name": slot.name,
            "start_time": str(slot.start_time),
            "end_time": str(slot.end_time),
            "status": slot.status,
            "slot_type": slot.slot_type or "Einzelstunde",
            "slot_icon": slot_icon,
            "max_participants": max_p,
            "current_participants": current_p,
            "horse_name": ", ".join(horse_names) if horse_names else None,
            "horse_id": horse_ids[0] if horse_ids else None,
            "facility_name": frappe.db.get_value("RS Facility", slot.facility, "facility_name") if slot.facility else None,
            "rider_name": ", ".join(rider_names) if rider_names else None,
            "rider_id": rider_ids[0] if rider_ids else None,
            "logbook_entry": slot.logbook_entry or "",
            "participants": participants_list
        })

    # Korrekte Zeitsortiering (HH:MM:SS als String)
    return sorted(result, key=lambda x: str(x["start_time"]))


@frappe.whitelist()
def save_logbook_entry(slot_name, entry, rider_id=None):
    """Speichert einen Logbuch-Eintrag für einen Slot oder Teilnehmer"""
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

    if rider_id and len(slot.participants) > 1:
        # Eintrag pro Teilnehmer direkt in DB
        for p in slot.participants:
            if p.rider == rider_id:
                frappe.db.sql("""
                    UPDATE `tabRS Slot Participant` 
                    SET logbook_entry = %s 
                    WHERE name = %s
                """, (entry, p.name))
                break
    else:
        # Einzelstunde: Eintrag am Slot
        slot.logbook_entry = entry
        slot.save(ignore_permissions=True)

    frappe.db.commit()
    return {"success": True}


@frappe.whitelist()
def get_rider_history(rider_name):
    """Gibt die Historie eines Reitschülers zurück"""
    if frappe.session.user == "Guest":
        frappe.throw("Nicht eingeloggt")

    # Nur Reitlehrer und Backoffice dürfen das sehen
    roles = frappe.get_roles(frappe.session.user)
    if not any(r in roles for r in ["Riding School Instructor", "Riding School Backoffice", "System Manager"]):
        frappe.throw("Keine Berechtigung")

    rider = frappe.get_doc("RS Rider", rider_name)

    # Vergangene Buchungen
    bookings = frappe.get_all(
        "RS Booking",
        filters={"rider": rider_name, "status": ["in", ["Completed", "Reserved", "Confirmed"]]},
        fields=["name", "lesson_slot", "billing_type"],
        order_by="creation desc",
        limit=20
    )

    history = []
    for b in bookings:
        slot = frappe.get_doc("RS Lesson Slot", b.lesson_slot)
        if slot.status not in ["Completed", "Booked"]:
            continue

        instructor_name = frappe.db.get_value("RS Instructor", slot.instructor, "full_name") if slot.instructor else None
        horse_name = frappe.db.get_value("RS Horse", slot.horse, "horse_name") if slot.horse else None

        # Rider Log
        log = frappe.db.get_value(
            "RS Rider Log",
            {"rider": rider_name, "lesson_slot": slot.name},
            ["lesson_rating", "instructor_rating", "rider_comment"],
            as_dict=True
        )

        history.append({
            "slot_date": str(slot.slot_date),
            "start_time": str(slot.start_time),
            "end_time": str(slot.end_time),
            "status": slot.status,
            "instructor_name": instructor_name,
            "horse_name": horse_name,
            "logbook_entry": slot.logbook_entry or "",
            "lesson_rating": round((log.lesson_rating or 0) * 5) if log else 0,
            "rider_comment": log.rider_comment if log else ""
        })

    return {
        "rider": {
            "name": rider.name,
            "full_name": rider.full_name,
            "skill_level": rider.skill_level,
            "weight_kg": rider.weight_kg,
            "goal": rider.goal,
            "lesson_type": rider.lesson_type
        },
        "history": sorted(history, key=lambda x: (x["slot_date"], x["start_time"]), reverse=True)
    }


@frappe.whitelist()
def get_horse_history(horse_name):
    """Gibt die Historie eines Pferdes zurück"""
    if frappe.session.user == "Guest":
        frappe.throw("Nicht eingeloggt")

    roles = frappe.get_roles(frappe.session.user)
    if not any(r in roles for r in ["Riding School Instructor", "Riding School Backoffice", "System Manager"]):
        frappe.throw("Keine Berechtigung")

    horse = frappe.get_doc("RS Horse", horse_name)

    # Letzte Einsätze
    slots = frappe.get_all(
        "RS Lesson Slot",
        filters={
            "horse": horse_name,
            "status": ["in", ["Completed", "Booked"]],
        },
        fields=["name", "slot_date", "start_time", "end_time",
                "status", "instructor", "facility"],
        order_by="slot_date desc, start_time desc",
        limit=20
    )

    # Stunden heute und diese Woche
    from datetime import date, timedelta
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    hours_today = frappe.db.sql("""
        SELECT SUM(TIME_TO_SEC(TIMEDIFF(end_time, start_time)) / 3600)
        FROM `tabRS Lesson Slot`
        WHERE horse = %s AND slot_date = %s AND status != 'Cancelled'
    """, (horse_name, today))[0][0] or 0

    hours_week = frappe.db.sql("""
        SELECT SUM(TIME_TO_SEC(TIMEDIFF(end_time, start_time)) / 3600)
        FROM `tabRS Lesson Slot`
        WHERE horse = %s AND slot_date >= %s AND status != 'Cancelled'
    """, (horse_name, week_start))[0][0] or 0

    history = []
    for s in slots:
        instructor_name = frappe.db.get_value("RS Instructor", s.instructor, "full_name") if s.instructor else None
        facility_name = frappe.db.get_value("RS Facility", s.facility, "facility_name") if s.facility else None

        booking = frappe.db.get_value(
            "RS Booking",
            {"lesson_slot": s.name, "status": ["!=", "Cancelled"]},
            ["rider"],
            as_dict=True
        )
        rider_name = frappe.db.get_value("RS Rider", booking.rider, "full_name") if booking else None

        history.append({
            "slot_date": str(s.slot_date),
            "start_time": str(s.start_time),
            "end_time": str(s.end_time),
            "status": s.status,
            "instructor_name": instructor_name,
            "facility_name": facility_name,
            "rider_name": rider_name
        })

    return {
        "horse": {
            "name": horse.name,
            "horse_name": horse.horse_name,
            "status": horse.status,
            "max_weight_kg": horse.max_weight_kg,
            "max_hours_per_day": horse.max_hours_per_day,
            "rest_minutes": horse.rest_minutes,
            "health_notes": horse.health_notes,
            "hours_today": round(float(hours_today), 1),
            "hours_week": round(float(hours_week), 1)
        },
        "history": history
    }


@frappe.whitelist()
def get_horse_notes(horse_name):
    """Gibt alle Notizen eines Pferdes zurück"""
    notes = frappe.get_all(
        "RS Horse Note",
        filters={"horse": horse_name},
        fields=["name", "note_date", "category", "note"],
        order_by="note_date desc"
    )
    return notes


@frappe.whitelist()
def save_horse_note(horse_name, category, note, note_date=None):
    """Speichert eine neue Notiz für ein Pferd"""
    if frappe.session.user == "Guest":
        frappe.throw("Nicht eingeloggt")

    roles = frappe.get_roles(frappe.session.user)
    if not any(r in roles for r in ["Riding School Instructor", "Riding School Backoffice", "System Manager"]):
        frappe.throw("Keine Berechtigung")

    from datetime import date
    doc = frappe.get_doc({
        "doctype": "RS Horse Note",
        "horse": horse_name,
        "note_date": note_date or str(date.today()),
        "category": category,
        "note": note
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True, "name": doc.name}


@frappe.whitelist()
def delete_horse_note(note_name):
    """Löscht eine Notiz"""
    if frappe.session.user == "Guest":
        frappe.throw("Nicht eingeloggt")

    frappe.delete_doc("RS Horse Note", note_name, ignore_permissions=True)
    frappe.db.commit()
    return {"success": True}
