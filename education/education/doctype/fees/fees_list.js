frappe.listview_settings["Fees"] = {
  add_fields: ["grand_total", "outstanding_amount", "due_date", "is_return"],
  get_indicator: function (doc) {
    if (doc.is_return == 1) {
      return [__("Refund"), "gray", "is_return,=,1"];
    } else if (flt(doc.outstanding_amount) == 0) {
      return [__("Paid"), "green", "outstanding_amount,=,0"];
    } else if (
      flt(doc.outstanding_amount) > 0 &&
      doc.due_date >= frappe.datetime.get_today()
    ) {
      return [
        __("Unpaid"),
        "orange",
        "outstanding_amount,>,0|due_date,>,Today",
      ];
    } else if (
      flt(doc.outstanding_amount) > 0 &&
      doc.due_date < frappe.datetime.get_today()
    ) {
      return [__("Overdue"), "red", "outstanding_amount,>,0|due_date,<=,Today"];
    }
  },
};
