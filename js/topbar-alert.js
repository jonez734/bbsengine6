// inspired by http://caolanmcmahon.com/files/jquery.notify.js/examples/index.html
'use strict';

let displaylist = [];

function showalert(sticky, id, fragment) {
  const container = $("ul#alerts");
  if (container.length === 0)
  {
    const newContainer = $('<ul id="alerts"></ul>').appendTo(document.body);
    be.logentry("created empty alerts container");
  }

  displaylist.push(id);

  const li = $("<li/>");
  li.data("alertid", id);
  li.css("opacity", 0.00);
  li.html(be.sanitize(fragment));
  li.appendTo(container);
  li.animate({ opacity: 1.0 }, 500);

  const closebutton = li.find(".closebutton");
  closebutton.click(function(event) {
    const foo = $(this).parent().parent();
    const alertid = foo.data("alertid");
    const idx = displaylist.indexOf(alertid);
    if (idx > -1)
    {
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

  const be = getbbsengine();
  if (be === null)
  {
    console.log("topbar-alert.100: be is null");
  }

  be.gettopbarupdateinterval().then(function(updateinterval) {
      be.addinterval(updateinterval, "poll for undisplayed notifies", function() {
        if (displaylist.length > 0)
        {
          $.ajax({
            type: "GET",
            dataType: "jsonp",
            url: ENGINEURL+"bed?req=alert.list&callback=?",
            data: { "displaylist[]": displaylist },
            done: function(alert)
            {
              if (typeof(alert.some) != "undefined") {
                alert.some(function (value, index, array) {
                  if ($.inArray(array[index].id, displaylist) === -1)
                  {
                    showalert(array[index].sticky, array[index].id, array[index].html);
                  }
                });
              }
            }
          });
        }
      });
  });
  be.gettopbarupdateinterval()
    .then(function(updateinterval) {
      be.addinterval(updateinterval, "update unread alert count", function() {
        be.updatetopbaritem("alertcount", ".alertcount");
      });
    });
});
