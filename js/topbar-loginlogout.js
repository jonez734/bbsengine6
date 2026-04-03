/**
 * topbar-loginlogout.js - Update login/logout link in topbar
 * @description Polls for auth state changes
 */
$(document).ready(function() {
  'use strict';

  const UPDATE_INTERVAL_MS = 5000;

  const be = bbsengine();
  if (!be) {
    console.error("topbar-loginlogout.100: bbsengine() returned null");
    return;
  }

  be.addinterval(UPDATE_INTERVAL_MS, "update topbar.loginlogout", function() {
    be.updatetopbaritem("topbar.loginlogout", ".loginlogout");
  });
});