/**
 * topbar.js - Top navigation bar management
 * @description Handles fixed positioning, checksums, and polling
 */
$(document).ready(function() {
  'use strict';

  if (typeof ENGINEURL === "undefined") {
    console.error("topbar.100: ENGINEURL is not defined");
    return;
  }

  const topbar = $("#topbar");
  const be = bbsengine();

  if (!be) {
    console.error("topbar.110: bbsengine() returned null");
    return;
  }

  if (topbar.length === 0) {
    return;
  }

  if (typeof topbar.offset === "function") {
    const offset = topbar.offset();
    if (typeof offset === "object") {
      const navPos = offset.top;

      $(window).scroll(function() {
        const fixIT = $(this).scrollTop() >= navPos;

        if (fixIT === true) {
          topbar.addClass("fixed");
          be.logentry("topbar.120: added class 'fixed'");
        } else {
          topbar.removeClass("fixed");
          be.logentry("topbar.130: removed class 'fixed'");
        }
      });
    }
  }

  topbar.children().each(function() {
    const checksum = bbsengine().checksum($(this).html());
    $(this).data("checksum", checksum);
  });

  function polltopbar() {
    let oldtopbarfragment = topbar.html();
    let topbarfragment = topbar.html();

    $.ajax({
      method: "GET",
      dataType: "jsonp",
      url: ENGINEURL + "get-topbar-content?callback=?",
      error: function(jqxhr, textStatus, error) {
        const err = textStatus + ", " + error;
        topbar.html(be.sanitize(err));
        be.logentry("topbar.140: error calling get-topbar-content");
      },
      success: function(payload) {
        if (!payload) {
          be.logentry("topbar.150: empty payload");
          return;
        }
        const status = be.sanitize(payload.status);
        const data = payload.data;
        let topbarstatus = $("div#topbar .status");
        if (topbarstatus.length === 0) {
          topbarstatus = $('<div class="end status"></div>').appendTo(topbar);
          be.logentry("topbar.160: created status container");
        }
        topbarstatus.html("<div class='inner'>[" + status + "]</div>");
        topbarfragment = $.trim(data);
        oldtopbarfragment = $.trim(oldtopbarfragment);

        if (topbarfragment !== oldtopbarfragment) {
          be.logentry("topbar.170: updating topbar content");
          topbar.fadeOut({
            duration: 250,
            complete: function() {
              topbar.html(be.sanitize(topbarfragment));
              oldtopbarfragment = topbar.html();
              topbar.fadeIn(250);
            }
          });
        }
      }
    });
  }
});