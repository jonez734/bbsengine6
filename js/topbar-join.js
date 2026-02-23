$(document).ready(function() {
  const be = getbbsengine();
  const $join = $("div#topbar .join");
  if (be)
  {
    be.addinterval(5000, "update join url", function () {
      be.updatetopbaritem("join", $join, "/get-topbar-join?callback=?");
    });
  }
  return;
}); /* end document.ready() */
