/**
 * checkcurrentmemberid.js - Check and log current member info
 * @description Fetches current user moniker for debugging/audit
 */
$(document).ready(function() {
  'use strict';

  async function checkcurrentmemberid() {
    const be = bbsengine();
    if (!be) {
      console.error("checkcurrentmemberid.100: bbsengine() returned null");
      return;
    }

    try {
      const currentmoniker = await be.getcurrentmoniker();
      be.logentry("checkcurrentmemberid.110: currentmoniker=" + JSON.stringify(currentmoniker));
    } catch (err) {
      console.error("checkcurrentmemberid.120: error fetching moniker:", err);
    }
  }

  checkcurrentmemberid();
});