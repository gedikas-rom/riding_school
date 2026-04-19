import frappe
from frappe import _
from datetime import datetime, timedelta
import datetime as dt


WEEKDAY_MAP = {
    "Montag": 0,
    "Dienstag": 1,
    "Mittwoch": 2,
    "Donnerstag": 3,
    "Freitag": 4,
    "Samstag": 5,
    "Sonntag": 6
}

CONFIG_WEEKDAY_MAP = {
    0: "monday",
    1: "tuesday",
    2: "wednesday",
    3: "thursday",
    4: "friday",
    5: "saturday",
    6: "sunday"
}


def timedelta_to_time(td):
    """Konvertiert timedelta zu time Objekt"""
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return dt.time(hours, minutes, seconds)


@frappe.whitelist()
def check_existing_slots(week_start_date):
    """Prüft ob bereits offene Slots für diese Woche existieren"""
    from datetime import datetime, timedelta
    week_start = datetime.strptime(week_start_date, "%Y-%m-%d").date()
    week_end = week_start + timedelta(days=6)
    
    count = frappe.db.count("RS Lesson Slot", {
        "slot_date": ["between", [week_start, week_end]],
        "status": "Open"
    })
    return {"existing_count": count}


@frappe.whitelist()
def delete_open_slots_for_week(week_start_date):
    """Löscht alle offenen Slots für eine Woche"""
    from datetime import datetime, timedelta
    week_start = datetime.strptime(week_start_date, "%Y-%m-%d").date()
    week_end = week_start + timedelta(days=6)
    
    slots = frappe.get_all("RS Lesson Slot", 
        filters={
            "slot_date": ["between", [week_start, week_end]],
            "status": "Open"
        },
        pluck="name"
    )
    for slot in slots:
        frappe.delete_doc("RS Lesson Slot", slot, ignore_permissions=True)
    frappe.db.commit()
    return {"deleted": len(slots)}


@frappe.whitelist()
def generate_slots_for_week(week_start_date):
    week_start = datetime.strptime(week_start_date, "%Y-%m-%d").date()

    config = frappe.get_single("RS Slot Config")
    slot_duration = int(config.slot_duration)
    break_duration = int(config.break_duration or 0)

    active_weekdays = []
    for day_num, field in CONFIG_WEEKDAY_MAP.items():
        if config.get(field):
            active_weekdays.append(day_num)

    if not active_weekdays:
        frappe.throw(_("Keine Wochentage in der Slot-Konfiguration aktiviert."))

    instructors = frappe.get_all("RS Instructor", fields=["name", "full_name"])

    slots_created = 0
    slots_skipped = 0

    for instructor in instructors:
        doc = frappe.get_doc("RS Instructor", instructor.name)

        if not doc.availability:
            continue

        for avail in doc.availability:
            weekday_num = WEEKDAY_MAP.get(avail.weekday)
            if weekday_num is None:
                continue

            if weekday_num not in active_weekdays:
                continue

            slot_date = week_start + timedelta(days=weekday_num)

            # timedelta zu time konvertieren
            from_time = timedelta_to_time(avail.from_time)
            to_time = timedelta_to_time(avail.to_time)

            from_dt = datetime.combine(slot_date, from_time)
            to_dt = datetime.combine(slot_date, to_time)

            current = from_dt
            while current + timedelta(minutes=slot_duration) <= to_dt:
                end = current + timedelta(minutes=slot_duration)

                existing = frappe.db.exists("RS Lesson Slot", {
                    "slot_date": slot_date,
                    "start_time": current.time(),
                    "instructor": instructor.name
                })

                if existing:
                    slots_skipped += 1
                else:
                    slot = frappe.get_doc({
                        "doctype": "RS Lesson Slot",
                        "slot_date": slot_date,
                        "start_time": current.time(),
                        "end_time": end.time(),
                        "instructor": instructor.name,
                        "status": "Open",
                        "slot_type": "Individual"
                    })
                    slot.insert(ignore_permissions=True)
                    slots_created += 1

                current = end + timedelta(minutes=break_duration)

    frappe.db.commit()

    return {
        "success": True,
        "slots_created": slots_created,
        "slots_skipped": slots_skipped,
        "message": f"{slots_created} Slots erstellt, {slots_skipped} bereits vorhanden."
    }


@frappe.whitelist()
def get_calendar_events(start, end, field_map, filters=None, doctype="RS Lesson Slot"):
    from frappe.utils import get_datetime, getdate
    import json

    events = frappe.get_all(
        "RS Lesson Slot",
        filters={
            "slot_date": ["between", [getdate(start), getdate(end)]],
            "status": ["!=", "Cancelled"]
        },
        fields=["name", "slot_date", "start_time", "end_time", "instructor", "horse", "status", "slot_type"]
    )

    STATUS_COLORS = {
        "Open": "#f5a623",
        "Planned": "#aed6f1",
        "Released": "#2e86c1",
        "Booked": "#a9dfbf",
        "Completed": "#27ae60",
        "Cancelled": "#e74c3c"
    }

    result = []
    for e in events:
        instructor_name = frappe.db.get_value("RS Instructor", e.instructor, "full_name") if e.instructor else "Kein Lehrer"
        horse_name = frappe.db.get_value("RS Horse", e.horse, "horse_name") if e.horse else "Kein Pferd"

        start_dt = f"{e.slot_date}T{str(e.start_time)}"
        end_dt = f"{e.slot_date}T{str(e.end_time)}"

        title = instructor_name
        if e.horse:
            title += f" / {horse_name}"
        title += f" [{e.status}]"

        result.append({
            "name": e.name,
            "title": title,
            "start": start_dt,
            "end": end_dt,
            "color": STATUS_COLORS.get(e.status, "#5e9bfc"),
            "allDay": 0
        })

    return result


@frappe.whitelist()
def release_all_planned_slots(week_start_date):
    """Gibt alle Planned Slots einer Woche frei"""
    from datetime import datetime, timedelta
    week_start = datetime.strptime(week_start_date, "%Y-%m-%d").date()
    week_end = week_start + timedelta(days=6)

    slots = frappe.get_all("RS Lesson Slot",
        filters={
            "slot_date": ["between", [week_start, week_end]],
            "status": "Planned"
        },
        pluck="name"
    )

    for slot_name in slots:
        frappe.db.set_value("RS Lesson Slot", slot_name, "status", "Released")

    frappe.db.commit()
    return {
        "success": True,
        "message": f"{len(slots)} Slots freigegeben."
    }


@frappe.whitelist()
def set_slot_status(slot_name, status):
    """Setzt den Status eines Slots"""
    allowed_transitions = {
        'Open': ['Planned', 'Cancelled'],
        'Planned': ['Open', 'Released', 'Cancelled'],
        'Released': ['Planned', 'Open', 'Booked', 'Completed', 'Cancelled'],
        'Booked': ['Completed', 'Cancelled'],
    }

    slot = frappe.get_doc("RS Lesson Slot", slot_name)
    allowed = allowed_transitions.get(slot.status, [])

    if status not in allowed:
        frappe.throw(
            _("Statusübergang von '{0}' nach '{1}' ist nicht erlaubt.").format(slot.status, status)
        )

    slot.status = status
    slot.save(ignore_permissions=True)

    # Bei Abschluss: Zeitkarte abbuchen
    if status == "Completed":
        booking = frappe.db.get_value(
            "RS Booking",
            {"lesson_slot": slot_name, "status": ["in", ["Reserved", "Confirmed"]], "billing_type": "Time Card"},
            ["name", "time_card"],
            as_dict=True
        )
        if booking and booking.time_card:
            tc = frappe.get_doc("RS Time Card", booking.time_card)
            tc.used_lessons = (tc.used_lessons or 0) + 1
            tc.remaining_lessons = (tc.total_lessons or 0) - tc.used_lessons
            if tc.remaining_lessons <= 0:
                tc.status = "Exhausted"
            tc.save(ignore_permissions=True)
            frappe.logger().info(f"Zeitkarte {tc.name} abgebucht: {tc.remaining_lessons} verbleibend")

        # Buchung auf Completed setzen
        frappe.db.set_value("RS Booking", 
            {"lesson_slot": slot_name, "status": ["!=", "Cancelled"]},
            "status", "Completed"
        )

    frappe.db.commit()
    return {"success": True, "status": status}
