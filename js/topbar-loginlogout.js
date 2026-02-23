$(document).ready(function() {
  if (be !== null)
  {
    be.addinterval(5000, "update topbar.loginlogout", function() {
      be.updatetopbaritem("topbar.loginlogout", $("div#topbar .loginlogout"), "/engine/bed?req=topbar.loginlogout&callback=?");
    });
  }
}); /* end document.ready() */
