$(document).ready(function () {
  'use strict';
  let foo = 1;

  const be = bbsengine();
  if (!be) {
    console.error("clock.js: bbsengine() returned null");
    return;
  }
  console.log("be="+JSON.stringify(be));
  
  be.addinterval(1000, "clock", updateclock);

  function updateclock()
  {
    const currentTime = new Date();
      
    let currentHours = currentTime.getHours();
    let currentMinutes = currentTime.getMinutes();

    currentMinutes = (currentMinutes < 10 ? "0" : "") + currentMinutes;
                  
    const meridian = (currentHours < 12) ? "AM" : "PM";
                       
    currentHours = (currentHours > 12) ? currentHours - 12 : currentHours;
    currentHours = (currentHours === 0) ? 12 : currentHours;
                               
    if (foo === 0)
    {
      $("#clock .flashingcolon").css("visibility", "visible");
    }
    else
    {
      $("#clock .flashingcolon").css("visibility","hidden");
    }
    $("#clock .currenthours").html(currentHours);
    $("#clock .currentminutes").html(currentMinutes);
    $("#clock .meridian").html(meridian);
    foo = 1 - foo;
  }
});
