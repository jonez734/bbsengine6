/**
 * bbsengine6.js - Core BBS engine module
 * @description Singleton providing AJAX, CSRF, sanitization, and interval management
 */
var bbsengine = (function() {
  /** @type {Object|null} */
  let instance = null;
  
  /** @type {Array} */
  let intervals = [];

  /** @type {RegExp} - Whitelist of valid request types */
  const VALID_REQUESTS = /^(currentmember\.moniker|currentmember\.id|config\.topbarupdateinterval|config\.getengineurl|join|topbar\.credits|topbar\.loginlogout|topbar\.greetings|nav|alert\.list|alert\.count)$/;

  /** @type {number} - Minimum interval in milliseconds */
  const MIN_INTERVAL_MS = 100;

  return function() {
    if (!instance) {
      instance = {
        /**
         * @description Log message to console if available
         * @param {string} message 
         */
        logentry: function(message) {
          if (typeof console === "object") {
            console.log(message);
          }
        },

        /**
         * @description Make AJAX request to bed endpoint
         * @param {string} req - Request type (validated against whitelist)
         * @param {boolean} [justcrc=false] - Return only checksum
         * @returns {Promise<Object>}
         * @throws {Error} If request type is invalid or AJAX fails
         */
        bedreq: async function(req, justcrc = false) {
          if (!VALID_REQUESTS.test(req)) {
            const error = new Error("Invalid request type: " + req);
            console.error(error.message);
            throw error;
          }

          this.logentry("bedreq.100: req=" + req + " justcrc=" + JSON.stringify(justcrc));

          try {
            return new Promise((resolve, reject) => {
              const csrfToken = this.getCsrfToken();
              let url = ENGINEURL + "bed?req=" + encodeURIComponent(req);
              if (justcrc === true) {
                url += "&justcrc";
              }
              url += "&callback=?";

              const ajaxOptions = {
                type: "GET",
                dataType: "jsonp",
                url: url,
                error: (xhr, textStatus, errorThrown) => {
                  console.error("bed error: textStatus=" + JSON.stringify(textStatus) + " errorThrown=" + JSON.stringify(errorThrown));
                  reject(new Error("Bed request failed: " + textStatus));
                },
                success: (data) => {
                  this.logentry("bedreq.200: data=" + JSON.stringify(data));
                  resolve(data);
                },
              };

              if (csrfToken) {
                ajaxOptions.beforeSend = function(xhr) {
                  xhr.setRequestHeader("X-CSRF-Token", csrfToken);
                };
              }

              $.ajax(ajaxOptions);
            });
          } catch (error) {
            if (error instanceof SyntaxError) {
              console.error("SyntaxError: " + error.message);
            } else {
              console.error("bedreq error: " + error.message);
            }
            throw error;
          }
        },

        /**
         * @description Get current user's moniker
         * @returns {Promise<string>}
         */
        getcurrentmoniker: async function() {
          const req = "currentmember.moniker";
          try {
            const data = await this.bedreq(req);
            return data[req];
          } catch (error) {
            console.error("error fetching " + req + ":", error.message);
            throw error;
          }
        },

        /**
         * @description Get current user's ID
         * @returns {Promise<string>}
         */
        getcurrentid: async function() {
          const req = "currentmember.id";
          try {
            const data = await this.bedreq(req);
            this.logentry("getcurrentid.100: data=" + JSON.stringify(data));
            return data[req];
          } catch (error) {
            console.error("error fetching " + req + ":", error.message);
            throw error;
          }
        },

        /**
         * @description Get topbar update interval from server
         * @returns {Promise<number>}
         */
        gettopbarupdateinterval: async function() {
          const req = "config.topbarupdateinterval";
          try {
            const data = await this.bedreq(req);
            return data[req];
          } catch (error) {
            console.error("error fetching " + req + ":", error.message);
            throw error;
          }
        },

        /**
         * @description Get engine URL
         * @returns {Promise<string>}
         */
        getengineurl: async function() {
          const req = "config.getengineurl";
          try {
            const data = await this.bedreq(req);
            return data[req];
          } catch (error) {
            console.error("error fetching " + req + ":", error.message);
            throw error;
          }
        },

        /**
         * @description Add a recurring interval
         * @param {number} interval - Interval in milliseconds
         * @param {string} note - Description of interval
         * @param {Function} func - Callback function
         */
        addinterval: function(interval, note, func) {
          if (interval === null || interval < MIN_INTERVAL_MS) {
            this.logentry("addinterval.100: " + note + ": invalid interval " + interval);
            return;
          }
          let id = setInterval(func, interval);
          if (!Array.isArray(this.intervals)) {
            this.intervals = [];
          }
          this.intervals.push([id, interval, func, note]);
          this.logentry("addinterval.110: id=" + id + " interval=" + interval + " note=" + note);
        },

        /**
         * @description Cancel all managed intervals
         */
        cancelintervals: function() {
          this.logentry("cancelintervals.100: canceling " + this.intervals.length + " intervals");
          this.intervals.forEach(function(item) {
            const id = item[0];
            clearInterval(id);
          });
          this.intervals = [];
        },

        /**
         * @description Restart all previously stored intervals
         */
        restartintervals: function() {
          this.logentry("restartintervals.100: restarting " + this.intervals.length + " intervals");
          this.intervals.forEach(function(item, index, arr) {
            const interval = item[1];
            const func = item[2];
            const note = item[3];
            const id = setInterval(func, interval);
            arr[index][0] = id;
          });
        },

        /**
         * @description Update a topbar item via AJAX
         * @param {string} req - Request type (validated against whitelist)
         * @param {string} [css=""] - jQuery selector suffix
         */
        updatetopbaritem: async function(req, css = "") {
          const selector = $("#topbar " + css);
          if (!selector || selector.length === 0) {
            this.logentry("updatetopbaritem.100: selector not found for css=" + css);
            return;
          }

          const origfragment = selector.clone().wrap("<div>").parent().html();
          if (origfragment === undefined) {
            this.logentry("updatetopbaritem.110: origfragment is undefined");
            return;
          }
          const origchecksum = this.checksum(origfragment);
          const response = await this.bedreq(req, true);
          if (response === undefined) {
            this.logentry("updatetopbaritem.120: response to " + JSON.stringify(req) + " is undefined");
            return;
          }

          if (response.checksum === undefined) {
            this.logentry("updatetopbaritem.130: response.checksum undefined");
            return;
          }

          this.logentry("updatetopbaritem.140: req=" + req + " origchecksum=" + origchecksum + " new=" + response.checksum);
          if (origchecksum === response.checksum) {
            this.logentry("updatetopbaritem.150: old and new match, skipping update");
            return;
          }

          this.logentry("updatetopbaritem.160: updating " + req);
          const csrfToken = this.getCsrfToken();
          let ajaxUrl = ENGINEURL + "bed?req=" + encodeURIComponent(req) + "&callback=?";

          const ajaxOptions = {
            type: "GET",
            dataType: "jsonp",
            url: ajaxUrl,
            error: (xhr, type, exception) => {
              const err = "textStatus=" + JSON.stringify(xhr) + " type=" + type + " exception=" + JSON.stringify(exception);
              this.logentry("updatetopbaritem.170: req for " + req + " failed: " + err);
            },
            success: (data) => {
              selector.fadeOut({
                duration: 350,
                complete: () => {
                  const cleanFragment = this.sanitize(data.fragment);
                  selector.replaceWith(cleanFragment);
                  selector.fadeIn(550);
                }
              });
            },
          };

          if (csrfToken) {
            ajaxOptions.beforeSend = function(xhr) {
              xhr.setRequestHeader("X-CSRF-Token", csrfToken);
            };
          }

          $.ajax(ajaxOptions);
        },

        /**
         * @description Calculate CRC32 checksum of string
         * @param {string} str 
         * @returns {string} - 8-character hex string
         */
        checksum: function(str) {
          let crc = 0xffffffff;
          for (let i = 0; i < str.length; i++) {
            crc ^= str.charCodeAt(i);
            for (let j = 0; j < 8; j++) {
              crc = (crc >>> 1) ^ (-(crc & 1) & 0xedb88320);
            }
          }
          crc ^= 0xffffffff;
          return ("00000000" + (crc >>> 0).toString(16)).slice(-8).toUpperCase();
        },

        /**
         * @description Sanitize HTML using DOMPurify, fallback to strip tags
         * @param {string} dirty - Raw HTML string
         * @returns {string} - Sanitized HTML
         * @throws {Error} If DOMPurify unavailable and fallback fails
         */
        sanitize: function(dirty) {
          if (typeof DOMPurify !== "undefined") {
            return DOMPurify.sanitize(dirty);
          }
          if (typeof console === "object") {
            console.error("DOMPurify not loaded - falling back to stripTags");
          }
          return stripTags(dirty);
        },

        /**
         * @description Get CSRF token from window object
         * @returns {string}
         */
        getCsrfToken: function() {
          return window.CSRF_TOKEN || "";
        },

      };
    }
    return instance;
  };
})();

/**
 * @description Strip all HTML tags (fallback sanitization)
 * @param {string} str 
 * @returns {string}
 */
function stripTags(str) {
  if (typeof str !== "string") {
    return "";
  }
  return str.replace(/<[^>]*>/g, "");
}