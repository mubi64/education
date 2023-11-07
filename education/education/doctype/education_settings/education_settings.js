// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Education Settings", {
  refresh: function (frm) {
    // frappe.msgprint("frm")
  },
});

frappe.ui.form.on("Discount Slabs", {
  from_month: function (frm, cdt, cdn) {
    for (let i = 0; i < frm.doc.discount_slabs.length; i++) {
      const ele = frm.doc.discount_slabs[i];
      if (ele.to_month != null) {
        if (ele.from_month > ele.to_month) {
          frappe.model.set_value(cdt, cdn, "from_month", ele.to_month);
          frappe.throw(__("From Month must be less then or equal-to To Month"));
        }
      }
    }
  },

  to_month: function (frm, cdt, cdn) {
    for (let i = 0; i < frm.doc.discount_slabs.length; i++) {
      const ele = frm.doc.discount_slabs[i];
      if (ele.from_month != null) {
        if (ele.to_month < ele.from_month) {
          frappe.model.set_value(cdt, cdn, "to_month", ele.from_month);
          frappe.throw(
            __("To Month must be greater then or equal-to From Month")
          );
        }
      }
    }
  },
});
