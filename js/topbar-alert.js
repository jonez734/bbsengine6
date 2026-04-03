/**
 * topbar-alert.js - Poll and display user alerts
 * @description Handles alert notifications with IIFE encapsulation
 */
(function() {
  'use strict';

  /** @type {Array<number>} - List of displayed alert IDs (private to IIFE) */
  let displaylist = [];

  /**
   * @description Display an alert notification
   * @param {boolean} sticky - Whether alert should remain until dismissed
   * @param {number} id - Alert ID
   * @param {string} fragment - HTML content for alert
   * @returns {jQuery}
   */
  function showalert(sticky, id, fragment) {
    let container = $("ul#alerts");
    if (container.length === 0) {
      container = $('<ul id="alerts"></ul>').appendTo(document.body);
      if (typeof be !== "undefined" && be) {
        be.logentry("topbar-alert.showalert.100: created alerts container");
      }
    }

    displaylist.push(id);

    const li = $("<li/>");
    li.data("alertid", id);
    li.css("opacity", 0.00);

    const sanitized = (typeof be !== "undefined" && be) ? be.sanitize(fragment) : fragment;
    li.html(sanitized);
    li.appendTo(container);
    li.animate({ opacity: 1.0 }, 500);

    const closebutton = li.find(".closebutton");
    closebutton.click(function() {
      const foo = $(this).parent().parent();
      const alertid = foo.data("alertid");
      const idx = displaylist.indexOf(alertid);
      if (idx > -1) {
        displaylist.splice(idx, 1);
      }

      foo.animate({ height: 0, opacity: 0.0 }, 500, function() {
        foo.remove();
        $("#alerts:empty").remove();
      });
    });

    return li;
  }

  $(document).ready(function() {
    const alertdiv = $("div#topbar .alertcount");
    if (alertdiv.length === 0) {
      return;
    }

    const be = bbsengine();
    if (!be) {
      console.error("topbar-alert.100: bbsengine() returned null");
      return;
    }

    be.gettopbarupdateinterval().then(function(updateinterval) {
      be.addinterval(updateinterval, "poll for undisplayed alerts", function() {
        if (displaylist.length > 0) {
          $.ajax({
            type: "GET",
            dataType: "jsonp",
            url: ENGINEURL + "bed?req=alert.list&callback=?",
            data: { "displaylist[]": displaylist },
            error: function(jqxhr, textStatus, errorThrown) {
              be.logentry("topbar-alert.110: AJAX error - " + textStatus + ": " + errorThrown);
            },
            success: function(alert) {
              if (typeof alert !== "undefined" && alert && typeof alert.some === "function") {
                alert.some(function(item) {
                  if ($.inArray(item.id, displaylist) === -1) {
                    showalert(item.sticky, item.id, item.html);
                  }
                });
              }
            }
          });
        }
      });

      be.addinterval(updateinterval, "update unread alert count", function() {
        be.updatetopbaritem("alertcount", ".alertcount");
      });
    }).catch(function(err) {
      console.error("topbar-alert.120: error getting interval:", err);
    });
  });
})();