// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.accounts.dimensions");

frappe.ui.form.on("Fee Structure", {
  setup: function (frm) {
    frm.add_fetch(
      "company",
      "default_receivable_account",
      "receivable_account"
    );
    frm.add_fetch("company", "default_income_account", "income_account");
    frm.add_fetch("company", "cost_center", "cost_center");
  },

  company: function (frm) {
    erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
  },

  onload: function (frm) {
    frm.set_query("academic_term", function () {
      return {
        filters: {
          academic_year: frm.doc.academic_year,
        },
      };
    });

    frm.set_query("receivable_account", function (doc) {
      return {
        filters: {
          account_type: "Receivable",
          is_group: 0,
          company: doc.company,
        },
      };
    });
    frm.set_query("income_account", function (doc) {
      return {
        filters: {
          account_type: "Income Account",
          is_group: 0,
          company: doc.company,
        },
      };
    });

    erpnext.accounts.dimensions.setup_dimension_filters(frm, frm.doctype);
  },

  refresh: function (frm) {
    if (frm.doc.docstatus === 1) {
      frm
        .add_custom_button(__("Create Fee Schedule"), function () {
          frm.events.make_fee_schedule(frm);
        })
        .addClass("btn-primary");
    }
    frm.fields_dict.components.grid.update_docfield_property(
      "discount_type",
      "hidden",
      1
    );
    frm.fields_dict.components.grid.update_docfield_property(
      "discount_amount",
      "hidden",
      1
    );
    frm.fields_dict.components.grid.update_docfield_property(
      "percentage",
      "hidden",
      1
    );
    refresh_field("components");
  },

  make_fee_schedule: function (frm) {
    frappe.model.open_mapped_doc({
      method:
        "education.education.doctype.fee_structure.fee_structure.make_fee_schedule",
      frm: frm,
    });
  },
});

frappe.ui.form.on("Fee Component", {
  //   discount_type: function (frm) {
  //     var com = frm.doc.components;
  //     for (var i = 0; i < com.length; i++) {
  //       var ele = com[i];
  //       if (ele.discount_type == "Amount") {
  //         ele.percentage = 0;
  //         frm.fields_dict.components.grid.update_docfield_property(
  //           "discount_amount",
  //           "read_only",
  //           0
  //         );
  //         frm.fields_dict.components.grid.update_docfield_property(
  //           "percentage",
  //           "read_only",
  //           1
  //         );
  //       }

  //       if (ele.discount_type == "Percentage") {
  //         ele.discount_amount = 0;
  //         frm.fields_dict.components.grid.update_docfield_property(
  //           "discount_amount",
  //           "read_only",
  //           1
  //         );
  //         frm.fields_dict.components.grid.update_docfield_property(
  //           "percentage",
  //           "read_only",
  //           0
  //         );
  //       }
  //     }
  //     refresh_field("components");
  //   },
  amount: function (frm) {
    var total_amount = 0;
    for (var i = 0; i < frm.doc.components.length; i++) {
      total_amount += frm.doc.components[i].amount;
    }
    frm.set_value("total_amount", total_amount);
  },
});
