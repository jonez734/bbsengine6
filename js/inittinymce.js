'use strict';

const be = bbsengine();
if (be) {
  be.logentry("calling tinymce.init");
}

if (typeof tinymce !== 'undefined') {
  tinymce.init({
   selector: 'textarea',
   plugins: [
    'hr emoticons advlist autolink lists link image charmap print preview anchor',
    'searchreplace visualblocks fullscreen',
    'insertdatetime media paste help wordcount'
    ],
    toolbar: 'insert | undo redo | formatselect | bold italic | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | removeformat | help',
    convert_fonts_to_spans: true,
    fix_list_elements: true,
    force_hex_style_colors: true,
    remove_trailing_brs: true,
    schema: 'html5-strict',
    browser_spellcheck: true,
    contextmenu: true
  });
} else if (be) {
  be.logentry("tinymce not loaded");
}
