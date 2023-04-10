$(document).ready(function () {
  var topbar = $("#topbar");
  // var oldtopbarfragment = topbar.html();
  // var topbarfragment = topbar.html();
  
  be = getbbsengine();

  // sticky topbar
/*
  if (typeof topbar === "object" && typeof topbar.offset === "function")
  {
    var offset = topbar.offset();
    if (typeof offset === "object")
    {
      var navPos = offset.top;
      
      $(window).scroll(function() {
        var fixIT = $(this).scrollTop() >= navPos;
           
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
*/
/*
  $(".sidebaricon").click(function() {
    if ($(".sidebar").hasClass("open"))
    {
      $(".sidebar").removeClass("open");
      $(".sidebar").addClass("closed");
    }
    else
    {
      $(".sidebar").addClass("open");
      $(".sidebar").removeClass("closed");
    }
    
    if ($(".sidebaricon").hasClass("open"))
    {
      $(".sidebaricon").removeClass("open");
      $(".sidebaricon").addClass("closed");
    }
    else
    {
      $(".sidebaricon").addClass("open");
      $(".sidebaricon").removeClass("closed");
    }
  });
*/
  topbar.children().each(function() {
    hashcode = be.hashcode($(this).html());
    $(this).data("hashcode", hashcode); // be.hashcode($(this).html()));
    // be.logentry("hashcode="+JSON.stringify($(this).data("hashcode")));
  });
  
  function polltopbar()
  {
    var oldtopbarfragment = topbar.html();
    var topbarfragment = topbar.html();

    // be.logentry("polltopbar called!");
    $.ajax(
    {
        method: "GET",
        dataType: "jsonp",
        url: "/get-topbar-content?callback=?",
        error: function( jqxhr, textStatus, error ) {
          var err = textStatus + ', ' + error;
            topbar.html(err);
            be.logentry("error calling get-topbar-content");
        },
        always: function() {
          be.logentry("always");
        },
        success: function(payload) {
          // be.logentry("payload="+JSON.stringify(payload));
          status = payload.status;
          data = payload.data;
          var topbarstatus = $("div#topbar .status");
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
              complete: function(data) {
                topbar.html(topbarfragment);
                oldtopbarfragment = topbar.html();
                // be.logentry("set oldtopbarfragment="+oldtopbarfragment+"\n");
                // notifycount = parseInt(payload.unread, 10);
                // be.logentry("notifycount="+notifycount);
                topbar.fadeIn(250);
              }
            });
          }
//          else
//          {
//            // be.logentry("topbar.200: no topbar change");
//          }
        }
    });
  } /* function polltopbar */
  
//  be.addinterval(5000, "poll topbar", polltopbar);
});
