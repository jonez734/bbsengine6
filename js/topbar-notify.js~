// inspired by http://caolanmcmahon.com/files/jquery.notify.js/examples/index.html

function shownotify(sticky, id, fragment) {
  var container = $("ul#notifications");
  if (container.length === 0)
  {
    container = $('<ul id="notifications"></ul>').appendTo(document.body);
    be.logentry("created empty notifications container");
  }

  displaylist.push(id);

  var li = $("<li/>");
  li.data("notifyid", id);
  li.css("opacity", 0.00);
  li.html(fragment);
  li.appendTo(container);
  li.animate({ opacity: 1.0 }, 500);

  closebutton = li.find(".closebutton");
  closebutton.click(function(event) {
    var foo = $(this).parent().parent();
    var notifyid = foo.data("notifyid");
    index = displaylist.indexOf(notifyid);
    if (index > -1)
    {
      displaylist.splice(index, 1);
    }
  
    foo.animate({ height: 0, opacity: 0.0 }, 500, function() {
      foo.remove();
      $("#notifications:empty").remove();
    });
  });

  return li;
}; /* end shownotify */

$(document).ready(function() {
  var displaylist = [];
  var notifycount = -1;
  var notifydiv = $("div#topbar .notifycount");
  var notifystatusfragment = null;
  var oldnotifystatusfragment = notifydiv.html();

  var payload = null;

  var be = getbbsengine();
/*
  var notificationtimeout = setInterval(function () { 
*/

  be.gettopbarupdateinterval()
    .then(updateinterval)
    {
      be.addinterval(updateinterval, "poll for undisplayed notifies", function() {
        if (notifycount > 0)
        {
          $.ajax({
            type: "GET",
            dataType: "jsonp",
            url: "/get-notify-list?filter=delivered&callback",
            data: { "displaylist[]": displaylist },
            done: function(notify)
            {
              if (typeof(notify.some) != "undefined") {
                notify.some(function (value, index, array) {
                  if ($.inArray(array[index].id, displaylist) === -1)
                  {
                    shownotify(array[index].sticky, array[index].id, array[index].html);
                  }
                }); /* end notify.some */
              } /* check for undefined */
            }
          }); /* end .ajax call */
        } /* end notifycount > 0 check */
      }); /* end be.addinterval for undisplayed notifies */
    }
  be.gettopbarupdateinterval()
    .then(updateinterval)
    {
      be.addinterval(updateintrval, "update unread notify count", function() {
        be.updatetopbaritem("notifycount", $("div#topbar .notifycount"), "/get-notify-count?callback");
      }
    }
}); /* end document.ready() */
