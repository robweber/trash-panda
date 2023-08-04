function toggleFileBrowser(){
  if($('#file_browser').is(':visible'))
  {
    $('#file_browser').hide();
  }
  else
  {
    $('#file_browser').show();
  }

  return false;
}

function createFile(){
  selectPath($('#new_file_name').val());
}

function selectPath(path){

  // set path in form input
  $('#config_path').html(path);

  // close the file browser
  toggleFileBrowser();

  // load the chosen file
  loadEditor();
}

function toggleDirSelect(){
  $('#directory_select_button').toggle();

  if($('#file_browser').is(':visible')){
    // if currently browsing, refresh the file list
    loadFiles($('#file_path').html());
  }
}

// creates an onClick method based on a file path and name, optionally can change javascript function
function makePathLink(path, name, funcName = 'loadFiles'){
  return '<a href="#" onClick="return ' + funcName + '(\'' + path + '\')">' + name + '</a><br />';
}

function loadFiles(path){

  // send request to load file listings
  $.ajax({type: 'GET', contentType: 'application/json', url: '/api/browse_files/' + path, success: function(data, status, request){

    if(data.success)
    {

      // set the current full path
      $('#file_path').html(data.path)

      fileList = "";  // string with html to display contents of directory

      //create the UP Level icon, if not at root
      if(data.path != '/'){
        splitPath = data.path.split('/');
        splitPath.pop();

        fileList = makePathLink(splitPath.join('/'), '<i class="bi bi-arrow-90deg-up"></i> ..');
      }

      //build the html list
      for(i = 0; i < data.dirs.length; i++)
      {
        fileList = fileList + makePathLink(data.path + '/' + data.dirs[i], data.dirs[i]);
      }

      //build the html list
      for(i = 0; i < data.files.length; i++)
      {
        fileList = fileList + makePathLink(data.path + '/' + data.files[i], data.files[i], 'selectPath');
      }

      $('#file_list').html(fileList);
    }
  }});

  return false;
}

function loadEditor(){
  $.ajax({type: 'POST', url: '/api/load_file', data: {'file_path': $('#config_path').html()}, success: function(data, status, request){
    editor.setValue(data,1);

    fileInfo = pathInfo($('#config_path').html());

    //set the mode based on the extension
    if(fileInfo['ext'] == '.yaml')
    {
      editor.session.setMode("ace/mode/yaml");
    }
    else if(fileInfo['ext'] == '.py')
    {
      editor.session.setMode("ace/mode/python");
    }
    else if(fileInfo['ext'] == '.md')
    {
      editor.session.setMode('ace/mode/markdown');
    }
    else
    {
      editor.session.setMode("ace/mode/plaintext");
    }

  }});
}

function saveFile(){
    $.post('/api/save_file', {'file_path': $('#config_path').html(), "file_contents":editor.getValue()}, function(data){
        //show success
        if(data.success)
        {
          //show message
          $('#js-success-alert').html(data.message);
          $('#js-success-alert').show().delay(3000).fadeOut();
        }
    });
}

function checkConfig(){
  $.get('/api/check_config', function(data){
    //show success or failure
    if(data.success)
    {
      //show message
      $('#js-success-alert').html(data.message);
      $('#js-success-alert').show().delay(3000).fadeOut();

      $('#validation_errors').html('');
    }
    else
    {
      //show message
      $('#js-error-alert').html(data.message);
      $('#js-error-alert').show().delay(3000).fadeOut();

      $('#validation_errors').html('Errors: ' + data.errors);
    }
  });
}

function pathInfo(s) {
    s=s.match(/(.*?\/)?(([^/]*?)(\.[^/.]+?)?)(?:[?#].*)?$/);
    return {path:s[1],file:s[2],name:s[3],ext:s[4]};
}
