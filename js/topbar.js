$(document).ready(function () {
  'use strict';
  const topbar = $("#topbar");
  const be = bbsengine();
  
  if (typeof topbar === "object" && typeof topbar.offset === "function")
  {
    const offset = topbar.offset();
    if (typeof offset === "object")
    {
      const navPos = offset.top;
      
      $(window).scroll(function() {
        const fixIT = $(this).scrollTop() >= navPos;
           
        if (fixIT === true)
        {
          topbar.addClass("fixed");
          be.logentry("topbar added class 'fixed'");
        }
        else
        {
          topbar.removeClass("fixed");
          be.logentry("topbar removed class 'fixed'");
        }
      });
    }
  }

  topbar.children().each(function() {
    const checksum = bbsengine().checksum($(this).html());
    $(this).data("checksum", checksum);
  });
  
  function polltopbar()
  {
    let oldtopbarfragment = topbar.html();
    let topbarfragment = topbar.html();

    $.ajax(
    {
        method: "GET",
        dataType: "jsonp",
        url: "/get-topbar-content?callback=?",
        error: function( jqxhr, textStatus, error ) {
          const err = textStatus + ', ' + error;
          topbar.html(be.sanitize(err));
          be.logentry("error calling get-topbar-content");
        },
        always: function() {
          be.logentry("always");
        },
        success: function(payload) {
          const status = be.sanitize(payload.status);
          const data = payload.data;
          let topbarstatus = $("div#topbar .status");
          if (topbarstatus.length === 0)
          {
            topbarstatus = $('<div class="end status"></div>').appendTo(topbar);
            be.logentry("created status container");
          }
          topbarstatus.html("<div class='inner'>["+status+"]</div>");
          topbarfragment = $.trim(data);
          be.logentry("topbarfragment="+topbarfragment);
          oldtopbarfragment = $.trim(oldtopbarfragment);
          be.logentry("oldtopbarfragment="+oldtopbarfragment);

          if (topbarfragment !== oldtopbarfragment)
          {
            be.logentry("fade out topbarfragment");
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
