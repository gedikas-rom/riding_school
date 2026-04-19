frappe.views.calendar["RS Rider Log"] = {
    field_map: {
        start: "log_date",
        end: "log_date",
        id: "name",
        title: "rider",
        allDay: 0
    },
    get_events_method: "frappe.desk.calendar.get_events"
};
