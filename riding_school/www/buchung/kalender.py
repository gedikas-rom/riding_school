import frappe

no_cache = True

def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/buchung"
        raise frappe.Redirect

    # Rollen des Users
    user_roles = frappe.get_roles(frappe.session.user)
    is_rider = "Riding School Rider" in user_roles
    is_instructor = "Riding School Instructor" in user_roles
    is_backoffice = "Riding School Backoffice" in user_roles or "System Manager" in user_roles

    # Rider-Daten laden
    rider = frappe.db.get_value(
        "RS Rider",
        {"user": frappe.session.user},
        ["name", "full_name", "skill_level", "weight_kg"],
        as_dict=True
    )

    # Instructor-Daten laden
    instructor = frappe.db.get_value(
        "RS Instructor",
        {"user": frappe.session.user},
        ["name", "full_name"],
        as_dict=True
    )

    context.no_header = True
    context.no_footer = True
    context.title = "Mein Portal"
    context.user_email = frappe.session.user
    context.rider = rider or {}
    context.instructor = instructor or {}
    context.is_rider = is_rider or bool(rider)
    context.is_instructor = is_instructor or bool(instructor)
    context.is_backoffice = is_backoffice
    context.csrf_token = frappe.sessions.get_csrf_token()
    context.display_name = (rider and rider.full_name) or \
                           (instructor and instructor.full_name) or \
                           frappe.session.user

    # Zeitkarten laden
    if rider:
        time_cards = frappe.get_all(
            "RS Time Card",
            filters={"rider": rider.name, "status": "Active"},
            fields=["name", "total_lessons", "used_lessons", "remaining_lessons", "valid_until"]
        )
        context.time_cards = time_cards
    else:
        context.time_cards = []
