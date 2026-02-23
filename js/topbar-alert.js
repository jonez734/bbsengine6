// inspired by http://caolanmcmahon.com/files/jquery.notify.js/examples/index.html

function showalert(sticky, id, fragment) {
  var container = $("ul#alerts");
  if (container.length === 0)
  {
    container = $('<ul id="alerts"></ul>').appendTo(document.body);
    be.logentry("created empty alerts container");
  }

  displaylist.push(id);

  var li = $("<li/>");
  li.data("alertid", id);
  li.css("opacity", 0.00);
  li.html(fragment);
  li.appendTo(container);
  li.animate({ opacity: 1.0 }, 500);

  closebutton = li.find(".closebutton");
  closebutton.click(function(event) {
    var foo = $(this).parent().parent();
    var alertid = foo.data("alertid");
    index = displaylist.indexOf(alertid);
    if (index > -1)
    {
      displaylist.splice(index, 1);
    }
  
    foo.animate({ height: 0, opacity: 0.0 }, 500, function() {
      foo.remove();
      $("#alerts:empty").remove();
    });
  });

  return li;
} /* end showalert */

$(document).ready(function() {
  var displaylist = [];
  var alertcount = -1;
  var alertdiv = $("div#topbar .alertcount");
  var alertstatusfragment = null;
  var oldalertstatusfragment = alertdiv.html();

  var payload = null;

  var be = getbbsengine();
  if (be === null)
  {
    console.log("topbar-alert.100: be is null");
  }
/*
  var notificationtimeout = setInterval(function () { 
*/

  be.gettopbarupdateinterval().then(updateinterval) {
      be.addinterval(updateinterval, "poll for undisplayed notifies", function() {
        if (alertcount > 0)
        {
          $.ajax({
            type: "GET",
            dataType: "jsonp",
            url: ENGINEURL+"bed?req=alert.list&callback=?", // get-alert-list?filter=delivered&callback",
            data: { "displaylist[]": displaylist },
            done: function(alert)
            {
              if (typeof(alert.some) != "undefined") {
                alert.some(function (value, index, array) {
                  if ($.inArray(array[index].id, displaylist) === -1)
                  {
                    showalert(array[index].sticky, array[index].id, array[index].html);
                  }
                }); /* end alert.some */
              } /* check for undefined */
            }
          }); /* end .ajax call */
        } /* end alertcount > 0 check */
      }); /* end be.addinterval for undisplayed notifies */
    }
  be.gettopbarupdateinterval()
    .then(updateinterval)
    {
      be.addinterval(updateintrval, "update unread alert count", function() {
        be.updatetopbaritem("alertcount", ".alertcount"); // $("div#topbar .alertcount"), ENGINEURL+"bed?req=currentmember.alertcount&callback=?");
      });
    }
}); /* end document.ready() */
