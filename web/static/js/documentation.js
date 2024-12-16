/*
highlights code blocks so that they can be copied. Works with both inline and full code blocks

To use create with c = DocumentationCopier(); and prep the links with c.prepare();
*/

class DocumentationCopy {
  constructor(object_name = 'copier'){
    this.OBJECT_NAME = object_name;
  }

  prepare(){
    // add copy link to all code blocks
    $('pre code').append(`<a href="#" onClick="return ${this.OBJECT_NAME}.copyTextBlock(this)" class="mdi mdi-content-copy icon-sm icon-inline code-copy-block"></a>`);

    // add to inline code
    $('p code').wrap(`<a href="#" class="code" onClick="return ${this.OBJECT_NAME}.copyTextLine(this)"></a>`);
    $('li code').wrap(`<a href="#" class="code" onClick="return ${this.OBJECT_NAME}.copyTextLine(this)"></a>`);
  }

  copyTextLine(element){
    // copy text within this link
    this.copyText($(element).text());

    // flash text to indicate success
    $(element).fadeOut(400).fadeIn(400);
    return false;
  }

  copyTextBlock(element){
    // copy entire text block
    this.copyText($(element).parent().text());

    // show check mark to user
    $(element).removeClass('mdi-content-copy').addClass('mdi-check text-success');
    setTimeout(function(){
      $(element).removeClass('mdi-check text-success').addClass('mdi-content-copy');
    }, 700);

    return false;
  }

  copyText(text){
    // create fake textarea to select the text
    var temp = $("<textarea>");
    $("body").append(temp);

    // copy text
    temp.val(text).select();
    var successful = document.execCommand('copy');

    // remove fake input
    temp.remove();
  }

}
