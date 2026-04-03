/**
 * topbar-join.js - Update join link in topbar
 * @description Polls for join link changes
 */
$(document).ready(function() {
  'use strict';

  const UPDATE_INTERVAL_MS = 5000;

  const be = bbsengine();
  if (!be) {
    console.error("topbar-join.100: bbsengine() returned null");
    return;
  }

  const $join = $("div#topbar .join");
  if ($join.length === 0) {
    return;
  }

  be.addinterval(UPDATE_INTERVAL_MS, "update join url", function() {
    be.updatetopbaritem("join", ".join");
  });
});