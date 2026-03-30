$(document).ready(function() {
  'use strict';
  const be = bbsengine();
  const $join = $("div#topbar .join");
  if (be)
  {
    be.addinterval(5000, "update join url", function () {
      be.updatetopbaritem("join", ".join");
    });
  }
});
