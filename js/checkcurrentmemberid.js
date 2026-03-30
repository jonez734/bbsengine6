$(document).ready(function () {
  'use strict';
  
  async function checkcurrentmemberid()
  {
    const be = bbsengine();
    if (!be) {
      console.error("checkcurrentmemberid.js: bbsengine() returned null");
      return;
    }
    const currentmoniker = await be.getcurrentmoniker();
    be.logentry("currentmoniker="+JSON.stringify(currentmoniker));
  }
  
  checkcurrentmemberid();
});
