import frappe

no_cache = True

def get_context(context):
    # Bereits eingeloggt → weiterleiten
    if frappe.session.user != "Guest":
        frappe.local.flags.redirect_location = "/buchung/kalender"
        raise frappe.Redirect

    context.no_header = True
    context.no_footer = True
    context.title = "Buchungsportal – Reitschule"
