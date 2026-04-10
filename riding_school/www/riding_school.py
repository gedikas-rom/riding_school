import frappe

def get_context(context):
    frappe.local.flags.redirect_location = "/app/riding-school"
    raise frappe.Redirect
