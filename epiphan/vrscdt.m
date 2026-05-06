% For file version and change log, see associated file
% vrscdt_change_log.txt

function varargout = vrscdt(varargin)
% VRSCDT M-file for vrscdt.fig
%      VRSCDT, by itself, creates a new VRSCDT or raises the existing
%      singleton*.
%
%      H = VRSCDT returns the handle to a new VRSCDT or the handle to
%      the existing singleton*.
%
%      VRSCDT('CALLBACK',hObject,eventData,handles,...) calls the local
%      function named CALLBACK in VRSCDT.M with the given input arguments.
%
%      VRSCDT('Property','Value',...) creates a new VRSCDT or raises the
%      existing singleton*.  Starting from the left, property value pairs are
%      applied to the GUI before vrscdt_OpeningFcn gets called.  An
%      unrecognized property name or invalid value makes property
%      application
%      stop.  All inputs are passed to vrscdt_OpeningFcn via varargin.
%
%      *See GUI Options on GUIDE's Tools menu.  Choose "GUI allows only one
%      instance to run (singleton)".
%
% See also: GUIDE, GUIDATA, GUIHANDLES

% Edit the above text to modify the response to help vrscdt

% Last Modified by GUIDE v2.5 09-Mar-2012 11:01:33

% Begin initialization code - DO NOT EDIT
gui_Singleton = 1;
gui_State = struct('gui_Name',       mfilename, ...
    'gui_Singleton',  gui_Singleton, ...
    'gui_OpeningFcn', @vrscdt_OpeningFcn, ...
    'gui_OutputFcn',  @vrscdt_OutputFcn, ...
    'gui_LayoutFcn',  [] , ...
    'gui_Callback',   []);
if nargin && ischar(varargin{1})
    gui_State.gui_Callback = str2func(varargin{1});
end

if nargout
    [varargout{1:nargout}] = gui_mainfcn(gui_State, varargin{:});
else
    gui_mainfcn(gui_State, varargin{:});
end

% End initialization code - DO NOT EDIT
end

function closeRequest(src,evnt)

delete(gcf);
return;

%global globalFigureForImageBufferHandle;

debug('Function closeRequest called.');

% User-defined close request function
% to display a question dialog box
selection = questdlg('Are you sure you want to close this program?',...
    'Program close request',...
    'Yes','No','Yes');
switch selection,
    case 'Yes',
%         if exist('globalFigureForImageBufferHandle')
%            delete(globalFigureForImageBufferHandle); 
%         end
        delete(gcf);
    case 'No'
        return;
end

end

% --- Executes just before vrscdt is made visible.
function vrscdt_OpeningFcn(hObject, eventdata, handles, varargin)
% This function has no output args, see OutputFcn.
% hObject    handle to figure
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)
% varargin   command line arguments to vrscdt (see VARARGIN)

global globalSerialBaudRate;
globalSerialBaudRate = 19200;

global globalSerialTimeout;
globalSerialTimeout = 3; % Default is 10

global globalHandles;
globalHandles = handles;
    


global globalVerboseDebug;

globalVerboseDebug = 0;

global globalSendSerialPrimitiveAndWaitForBytesReverseLog;

globalSendSerialPrimitiveAndWaitForBytesReverseLog = '';

% Globals for emulation of circuits.
global globalPolygonClockIsDisable;
global globalTMR1ReloadValue; 
global globalNumberOfLinesPerFrame;
global globalDACIncrement;
global globalDACStart;
global globalNumberOfLinesForVSync;
globalTMR1ReloadValue = uint16(60327);
globalNumberOfLinesPerFrame = uint16(512 + 64);
globalDACIncrement = uint16(32);
globalDACStart = uint16((65535 / 2) - ((globalNumberOfLinesPerFrame / 2) * globalDACIncrement));
globalNumberOfLinesForVSync = uint16(6);

% globalTimeProgramWasStarted is handy to see if someone is leaving the
% program always running.
global globalTimeProgramWasStarted;
globalTimeProgramWasStarted = datestr(now);

global lastFileForSettings;
global globalCurrentVersion;
global globalCurrentVersionString;

lastFileForSettings = [mfilename '_settings.mat'];

% Choose default command line output for vrscdt
handles.output = hObject;

% Update handles structure
guidata(hObject, handles);

% UIWAIT makes vrscdt wait for user response (see UIRESUME)
% uiwait(handles.figure1);

%get(handles.figure1);

set(handles.figure1,'CloseRequestFcn',@closeRequest);

ports = getAvailableSerialPort();
ports{length(ports) + 1} = 'Emulate';

set(handles.serialInterfacePopupmenu,'String', ports);
set(handles.serialInterfacePopupmenu,'Value', length(ports));

set(handles.polygonSpeedControlCircuitSerialInterfacePopupmenu,'String', ports);
set(handles.polygonSpeedControlCircuitSerialInterfacePopupmenu,'Value', length(ports));

settingsLoadedFromFile = loadSettingsFromFile(mfilename, handles); % or at least try

if (settingsLoadedFromFile == 0)
    prompt = 'No settings were loaded from a file. It is highly recommended to use the interactive configuration process after initialization of the tool.';    
    uiwait(warndlg(prompt, 'Warning', 'modal'));    
end


changeLogFilename = [mfilename '_change_log.txt'];

[fid message] = fopen(changeLogFilename, 'r');

if (fid == -1)
    globalCurrentVersion = [0 0 0];
    globalCurrentVersionString = ['unknown: missing ' changeLogFilename];
    errorDialogAndStatus(sprintf([changeLogFilename ' ' message '. Cannot determine version of this program. You should get the zip file of the latest version to fix this.']), mfilename, handles);   
else
    fscanfFormat = ['%% ' mfilename ' version %d.%d.%d'];
    globalCurrentVersion = fscanf(fid, fscanfFormat);
    globalCurrentVersionString = sprintf('%d.%d.%d', globalCurrentVersion(1), globalCurrentVersion(2), globalCurrentVersion(3));
    fclose(fid);   
end

set(handles.versionEdit, 'String', globalCurrentVersionString);

disp(sprintf('Current version is: %s', globalCurrentVersionString));

if (fid == -1)
   return; 
end

skipNewVersionCheck = 0;

if (size(varargin) == [1 1])
    if (cell2mat(varargin(1,1)) == 1)
        skipNewVersionCheck = 1;
    else
        skipNewVersionCheck = 0;
    end
end

if (skipNewVersionCheck)
    disp('Checking for new version was skipped.')
else
    prompt = sprintf('Do you want to check for a new version?\n\nYou can skip this prompt by calling this program like this %s(1).', mfilename);    
    answer = questdlg(prompt, ...
        mfilename, ...
        'Yes', 'No', 'Yes');
    if (strcmp(answer, 'Yes'))      
        [versionComparison, latestVersion] = checkForNewVersion();
    end
end

%showFigureForEmulation(handles);
    
    %checkLatestMicrocontrollerFirmwareVersion();

end

function msgboxModal(message, newTitle)

if (exist('newTitle'))
   title = newTittle;
else
    title = mfilename;
end

uiwait(msgbox(message, title, 'modal'));

end

function [versionString] = convertVersionArrayToString(versionArray)

versionString = sprintf('%d.%d.%d', versionArray(1), versionArray(2), versionArray(3));

end


function [versionComparison, latestVersion] = checkForNewVersion

global globalCurrentVersion;

disp('Debug: Checking if internet is reachable.');

if (isnet() == 1)
    disp('Debug: Net seems to be reachable.');
else
    disp('Debug: Net is not reachable.');
    return;
end

disp('Checking for new version...')

latestVersionChangeLogURL = 'https://docs.google.com/uc?id=0B2oqdvmvAX40S2xqVzVVSmpUYzZJWEIzdWJnc1BZdw&export=download&hl=en_US';

latestVersionOfArchiveURL = 'https://docs.google.com/uc?id=0B2oqdvmvAX40b29yUFdWZ2lSejZqWk5CN3JJallRUQ&export=download&hl=en_US';

disp('Debug: About to call urlread. There is a risk of hanging some versions of Matlab here if internet is down.');
disp(sprintf('Debug: If this happens, kill MATLAB with the task manager and invoke the program with version checking disabled, i.e. %s(1)', mfilename));
[latestVersionChangeLog, status] = urlread(latestVersionChangeLogURL);
disp('Debug: urlread success.');

if (status == 1)
    scanfFormat = ['%% ' mfilename ' version %d.%d.%d'];
    latestVersion = sscanf(latestVersionChangeLog, scanfFormat);
    latestVersionString = convertVersionArrayToString(latestVersion);
    
    disp(sprintf('Latest version is: %s', latestVersionString));
    
    versionComparison = compareVersion(globalCurrentVersion, latestVersion);
    
    if (versionComparison == 1)
        prompt = sprintf('A newer version (%s) is available.\nDo you want to see the change log?', latestVersionString);
        % TBD Need non-modal here.
        answer = questdlg(prompt, ...
            'Newer version available', ...
            'Yes', 'No', 'Yes');
        if (strcmp(answer, 'Yes'))
            sizeOfLatestVersionChangeLog = size(latestVersionChangeLog);
            changeLog = ' ';
            for i = 1:(sizeOfLatestVersionChangeLog(2))
                if latestVersionChangeLog(i) == '$'
                    break;
                end
                changeLog = [changeLog latestVersionChangeLog(i)];
            end
            disp(changeLog);
%             changeLogFilename = [mfilename '_' latestVersionString];
%             changeLogFilename = strcat(changeLogFilename, '_change_log.txt');
%             fid = fopen(changeLogFilename, 'w');
%             fprintf(fid, '%s', changeLog);
%             fclose(fid);
%             edit(changeLogFilename);
            prompt = sprintf('Press enter to continue.\n');
            answer = input(prompt, 's');                             
        end
        
        prompt = sprintf(['Do you want to launch a web browser to fetch an archive containing the latest version?.\n\n' ...
            'Pathname of the files to update:\n\n%s\n%s\n' ...
            '\nNote that you will have to exit MATLAB to be able to overwrite the file(s).\n'], which(mfilename), which([mfilename '.fig']));
        answer = questdlg(prompt, ...
            'Launching browser to fetch the archive)?', ...
            'Yes', 'Yes and Quit MATLAB', 'No', 'Yes and Quit MATLAB');
        if (strcmp(answer, 'No'))
        else            
            % Yes or Yes and Quit MATLAB            
            web(latestVersionOfArchiveURL, '-browser');
            msgboxModal('Please click on the send button in the feedback form that will open in the web browser to inform the developper that a system is about to be updated.');
            debug('About to call submitFeedback');
            submitFeedback(sprintf('System is about to be updated to version %s.', latestVersionString))
            if (strcmp(answer, 'Yes and Quit MATLAB'))
                quit;
            end            
        end
        
    elseif (versionComparison < 0)
        msgboxModal(sprintf('This version (%d.%d.%d) is more recent than the one available on the Internet (%s).\n\nYou must be the developer. Mustn`t you?', globalCurrentVersion(1), globalCurrentVersion(2), globalCurrentVersion(3), latestVersionString));        
    else
        msgboxModal('This version is up to date.');
    end
else    
    msgboxModal('Could not check for new version. URL may be temporarily down.');
    versionComparison = 0;
    latestVersion = [0 0 0];
end


end

function debug(message)

global globalVerboseDebug;

if (globalVerboseDebug)
    disp(sprintf('Debug: %s', message));    
end

end

% --- Outputs from this function are returned to the command line.
function varargout = vrscdt_OutputFcn(hObject, eventdata, handles)
% varargout  cell array for returning output args (see VARARGOUT);
% hObject    handle to figure
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

% Get default command line output from handles structure
varargout{1} = handles.output;

debug('Debug: vrscdt_OutputFcn is executed.');

end

function showFigureForEmulation(handles)

global globalImageBuffer;

global globalFigureForImageBufferHandle;

%globalFigureForImageBufferHandle = figure(2);
handle = figure(2);
class(handles.figure1)
get(handle)
set(handles, 'figure2', figure(2));

globalImageBuffer = uint8(zeros(512));
image(globalImageBuffer);
colormap('gray');
axis off;
axis image;

end

% --- Executes on button press in getFirmwareVersionPushbutton.
function [error firmwareVersion] = getFirmwareVersionPushbutton_Callback(hObject, eventdata, handles)
% hObject    handle to getFirmwareVersionPushbutton (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

error = 0;

set(handles.firmwareVersionEdit,'String','Unknown');
set(handles.statusEdit,'String','Getting firmware version of the circuit...');
drawnow

expectedNumberOfBytes = 3;
bytesReturned = sendSerialPrimitiveAndWaitForBytes(handles, READ_FIRMWARE_VERSION, expectedNumberOfBytes);
firmwareVersion = bytesReturned;
if (numel(bytesReturned) < expectedNumberOfBytes)
    errorDialogAndStatus(sprintf('Error: could not get the expected number of bytes (%d) while reading firmware version of the circuit.', expectedNumberOfBytes), mfilename, handles);    
    error = 1;
    return;    
end

if (firmwareVersion ~= -1)
    firmwareVersionString = [num2str(firmwareVersion(1)), '.', num2str(firmwareVersion(2)), '.', num2str(firmwareVersion(3))];
    % need to convert the answer back into string type to display it
    set(handles.firmwareVersionEdit,'String',firmwareVersionString);    
else
    error = 1;
    msgboxModal('Error: could not get firmware version of the circuit.');  
end

set(handles.statusEdit,'String','');

end

function [latestVersion changeLog errorMessage] = getLatestMicrocontrollerFirmwareVersion(latestVersionOfMicrocontrollerFirmwareHeaderURL)

changeLog = '';
latestVersion = -1;
errorMessage = 'Could not get latest microcontroller firmware version. URL may be temporarily down.';

disp('Debug: About to call urlread. There is a risk of hanging some versions of MATLAB here if internet is down.');
disp('Debug: If this happens, kill MATLAB with the task manager and invoke the program with version checking disabled, i.e. pmticdt(1)');
[latestVersionOfMicrocontrollerFirmwareHeader, status] = urlread(latestVersionOfMicrocontrollerFirmwareHeaderURL);
disp('Debug: urlread success.');

if (status == 1)    
    latestVersion = sscanf(latestVersionOfMicrocontrollerFirmwareHeader,'#define FIRMWARE_VERSION_MAJOR %d\n#define FIRMWARE_VERSION_MINOR %d\n#define FIRMWARE_VERSION_TRIVIAL %d');
    latestVersionString = sprintf('%d.%d.%d', latestVersion(1), latestVersion(2), latestVersion(3));
    errorMessage = '';
    
    sizeOfLatestVersionOfMicrocontrollerFirmwareHeader = size(latestVersionOfMicrocontrollerFirmwareHeader);
    changeLog = ' ';
    for i = 1:sizeOfLatestVersionOfMicrocontrollerFirmwareHeader(2)
        if latestVersionOfMicrocontrollerFirmwareHeader(i) == '$'
            break;
        end
        changeLog = [changeLog latestVersionOfMicrocontrollerFirmwareHeader(i)];
    end
else
    latestVersion = -1;
    errorMessage = 'Could not get latest microcontroller firmware version. URL may be temporarily down.';
end

end


function serialInterfaceEdit_Callback(hObject, eventdata, handles)
% hObject    handle to serialInterfaceEdit (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of serialInterfaceEdit as text
%        str2double(get(hObject,'String')) returns contents of serialInterfaceEdit as a double

end

% --- Executes during object creation, after setting all properties.
function serialInterfaceEdit_CreateFcn(hObject, eventdata, handles)
% hObject    handle to serialInterfaceEdit (see GCBO)
% eventdata  reserved
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

end

function firmwareVersionEdit_Callback(hObject, eventdata, handles)
% hObject    handle to firmwareVersionEdit (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of firmwareVersionEdit as text
%        str2double(get(hObject,'String')) returns contents of firmwareVersionEdit as a double

end

% --- Executes during object creation, after setting all properties.
function firmwareVersionEdit_CreateFcn(hObject, eventdata, handles)
% hObject    handle to firmwareVersionEdit (see GCBO)
% eventdata  reserved
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

end

% --- If Enable == 'on', executes on mouse press in 5 pixel border.
% --- Otherwise, executes on mouse press in 5 pixel border or over getFirmwareVersionPushbutton.
function getFirmwareVersionPushbutton_ButtonDownFcn(hObject, eventdata, handles)
% hObject    handle to getFirmwareVersionPushbutton (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

end

function galvanometerStartValueEdit_Callback(hObject, eventdata, handles)
% hObject    handle to galvanometerStartValueEdit (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of galvanometerStartValueEdit as text
%        str2double(get(hObject,'String')) returns contents of galvanometerStartValueEdit as a double

galvanometerStartValueString = get(handles.galvanometerStartValueEdit,'String');

if (isempty(galvanometerStartValueString))
   msgboxModal('Set galvanometer start value first.');
   return;
end

galvanometerStartValue = str2num(galvanometerStartValueString);

if (galvanometerStartValue < 0 || galvanometerStartValue > 65535)
    msgboxModal('Galvanometer start value is outside valid range, i.e. 0 to 65535');
    return    
end

set(handles.statusEdit,'String', 'Writing galvanometer start value...');
drawnow

galvanometerStartValueMostSignificantByte = uint8(floor(galvanometerStartValue / 256))
galvanometerStartValueLeastSignificantByte = rem(galvanometerStartValue, 256)

bytesReturned = sendSerialPrimitiveAndWaitForBytes(handles, [WRITE_DAC_START uint8(galvanometerStartValueMostSignificantByte) uint8(galvanometerStartValueLeastSignificantByte)], 0);

if (bytesReturned == -1)
    msgboxModal('Error: Could not get galvanometer start value.');    
end

set(handles.statusEdit,'String','');
drawnow

end

% --- Executes during object creation, after setting all properties.
function galvanometerStartValueEdit_CreateFcn(hObject, eventdata, handles)
% hObject    handle to galvanometerStartValueEdit (see GCBO)
% eventdata  reserved
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

end

% --- Executes on button press in readStartValuePushbutton.
function readStartValuePushbutton_Callback(hObject, eventdata, handles)
% hObject    handle to readStartValuePushbutton (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

set(handles.statusEdit,'String','Reading start value...');
drawnow;

bytesReturned = sendSerialPrimitiveAndWaitForBytes(handles, READ_DAC_START, 2);

if (isempty(bytesReturned))
    msgboxModal('Error: Could not read start value.');
else
    galvanometerStartValueString = [num2str(bytesReturned(1) * 256 + bytesReturned(2))]
    % need to convert the answer back into String type to display it
    set(handles.galvanometerStartValueEdit,'String', galvanometerStartValueString);
    
end

set(handles.statusEdit,'String','');

end

function galvanometerIncrementEdit_Callback(hObject, eventdata, handles)
% hObject    handle to galvanometerIncrementEdit (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of galvanometerIncrementEdit as text
%        str2double(get(hObject,'String')) returns contents of galvanometerIncrementEdit as a double


galvanometerIncrementString = get(handles.galvanometerIncrementEdit,'String');

if (isempty(galvanometerIncrementString))
   msgboxModal('Set galvanometer increment first.');
   return;
end

galvanometerIncrement = str2num(galvanometerIncrementString);

if (galvanometerIncrement < 0 || galvanometerIncrement > 65535)
    msgboxModal('Galvanometer increment is outside valid range, i.e. 0 to 65535');
    return    
end

set(handles.statusEdit,'String', 'Writing galvanometer increment...');
drawnow

galvanometerIncrementMostSignificantByte = uint8(floor(galvanometerIncrement / 256))
galvanometerIncrementLeastSignificantByte = rem(galvanometerIncrement, 256)

bytesReturned = sendSerialPrimitiveAndWaitForBytes(handles, [WRITE_DAC_INCREMENT uint8(galvanometerIncrementMostSignificantByte) uint8(galvanometerIncrementLeastSignificantByte)], 0);

if (bytesReturned == -1)
    msgboxModal('Error: Could not write galvanometer increment.');    
end

set(handles.statusEdit,'String','');
drawnow

end

% --- Executes during object creation, after setting all properties.
function galvanometerIncrementEdit_CreateFcn(hObject, eventdata, handles)
% hObject    handle to galvanometerIncrementEdit (see GCBO)
% eventdata  reserved
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

end


% --- Executes on button press in readIncrementPushbutton.
function readIncrementPushbutton_Callback(hObject, eventdata, handles)
% hObject    handle to readIncrementPushbutton (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

set(handles.statusEdit,'String','Reading increment...');
drawnow

bytesReturned = sendSerialPrimitiveAndWaitForBytes(handles, READ_DAC_INCREMENT, 2);

if (isempty(bytesReturned))
    msgboxModal('Error: Could not read increment.');
else
    galvanometerIncrementString = [num2str(bytesReturned(1) * 256 + bytesReturned(2))]
    % need to convert the answer back into String type to display it
    set(handles.galvanometerIncrementEdit,'String', galvanometerIncrementString);
end

set(handles.statusEdit,'String','');

end

% --- Executes on button press in SaveSettingsToBankPushbutton.
function SaveSettingsToBankPushbutton_Callback(hObject, eventdata, handles, defaultBank)
% hObject    handle to SaveSettingsToBankPushbutton (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

numberOfLines = 1;

if (exist('defaultBank'))
    defaultAnswer={num2str(defaultBank)};
else
    defaultAnswer={'0'};
end

bankString = inputdlg('Bank number (valid range: 0 to 3). Settings are those currently used by circuit, not necessarily what is displayed in the tool.', mfilename, numberOfLines, defaultAnswer);

if (isempty(bankString))
    return;
end

bank = str2num(bankString{1});
if (bank < 0 || bank > 3)
    msgboxModal('Invalid bank number. Valid range is 0 to 3.');
    return;
end

SaveSettingsToBank(hObject, eventdata, handles, bank);

end

function SaveSettingsToBank(hObject, eventdata, handles, bank)

set(handles.statusEdit,'String','Saving settings to bank...');
drawnow
command = [WRITE_SETTINGS_TO_PRESET_BANK bank];
sendSerialPrimitiveAndWaitForBytes(handles, command, 0);

pause(1); % ************ This pause is mandatory or Matlab will freeze. **********************
set(handles.statusEdit,'String','');
drawnow;

end

% --- Executes on button press in LoadSettingsFromBankPushbutton.
function LoadSettingsFromBankPushbutton_Callback(hObject, eventdata, handles, defaultBank)
% hObject    handle to LoadSettingsFromBankPushbutton (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

numberOfLines=1;
if (exist('defaultBank'))
    defaultAnswer={num2str(defaultBank)};
else
    defaultAnswer = {'0'};
end

bankString = inputdlg('Bank number (valid range: 0 to 3)', mfilename, numberOfLines, defaultAnswer);

if (isempty(bankString))
    return;
end

bank = str2num(bankString{1});
if (bank < 0 || bank > 3)
    msgboxModal('Invalid bank number. Valid range is 0 to 3.');
    return;
end
set(handles.statusEdit,'String','Loading settings from bank...');
drawnow

command = [LOAD_SETTINGS_FROM_PRESET_BANK bank];
sendSerialPrimitiveAndWaitForBytes(handles, command, 0);

pause(1);

    selectedCircuitPopupmenu = handles.selectedCircuitPopupmenu;    
    selectedCircuitIndex = get(selectedCircuitPopupmenu,'Value');
    selectedCircuitStrings = get(selectedCircuitPopupmenu,'String');
    selectedCircuit = selectedCircuitStrings{selectedCircuitIndex};
    if (selectedCircuitIndex == 2)        
        readTMR1ReloadValuePushbutton_Callback(handles.readTMR1ReloadValuePushbutton, eventdata, handles);        
    else    
        % Video rate synchronization circuit
        readStartValuePushbutton_Callback(hObject, eventdata, handles);
        readIncrementPushbutton_Callback(hObject, eventdata, handles);        
        readNumberOfLinesPerFramePushbutton_Callback(handles.readNumberOfLinesPerFramePushbutton, eventdata, handles);
        readNumberOfLinesForVSyncPushbutton_Callback(handles.readNumberOfLinesForVSyncPushbutton, eventdata, handles);        
    end
end

function lSerial_Port = getAvailableSerialPort()
% function lSerial_Port = getAvailableSerialPort()
% Return a Cell Array of serial port names available on your computer

if (ispc())
    
    try
        s = serial('IMPOSSIBLE_NAME_ON_PORT');
        fopen(s);
    catch
        lErrMsg = lasterr;
    end
    
    %Start of the COM available port
    lIndex1 = findstr(lErrMsg,'COM');
    %End of COM available port
    lIndex2 = findstr(lErrMsg,'Use')-3;
    
    lSerialStr = lErrMsg(lIndex1:lIndex2);
    
    %Parse the resulting string
    lIndexDot = findstr(lSerialStr,',');
    
    % If no Port are available
    if isempty(lIndex1)
        lSerial_Port{1}='';
        return;
    end
    
    % If only one Port is available
    if isempty(lIndexDot)
        lSerial_Port{1}=lSerialStr;
        return;
    end
    
    lSerial_Port{1} = lSerialStr(1:lIndexDot(1)-1);
    
    for i=1:numel(lIndexDot)+1
        % First One
        if (i==1)
            lSerial_Port{1,1} = lSerialStr(1:lIndexDot(i)-1);
            % Last One
        elseif (i==numel(lIndexDot)+1)
            lSerial_Port{i,1} = lSerialStr(lIndexDot(i-1)+2:end);
            % Others
        else
            lSerial_Port{i,1} = lSerialStr(lIndexDot(i-1)+2:lIndexDot(i)-1);
        end
    end
else
    
    ttyString = ls('/dev/tty.*');
    tab = sprintf('\t');
    newline = sprintf('\n');
    counter = 1;
    previousIndex = 1;
    for i=1:length(ttyString)
        if ((ttyString(i) == tab) || (ttyString(i) == newline))
            lSerial_Port{counter,1} = ttyString(1,previousIndex:i - 1);
            counter = counter + 1;
            previousIndex = i + 1;
        end
    end
end

end
% --- Executes on selection change in serialInterfacePopupmenu.
function serialInterfacePopupmenu_Callback(hObject, eventdata, handles)
% hObject    handle to serialInterfacePopupmenu (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

% Hints: contents = get(hObject,'String') returns serialInterfacePopupmenu contents as cell array
%        contents{get(hObject,'Value')} returns selected item from serialInterfacePopupmenu

end

% --- Executes during object creation, after setting all properties.
function serialInterfacePopupmenu_CreateFcn(hObject, eventdata, handles)
% hObject    handle to serialInterfacePopupmenu (see GCBO)
% eventdata  reserved
% handles    empty - handles not created until after all CreateFcns called

% Hint: polygonspeedcontrolcircuitserialinterfacepopupmenu controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

end

function statusEdit_Callback(hObject, eventdata, handles)
% hObject    handle to statusEdit (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of statusEdit as text
%        str2double(get(hObject,'String')) returns contents of statusEdit as a double

end

% --- Executes during object creation, after setting all properties.
function statusEdit_CreateFcn(hObject, eventdata, handles)
% hObject    handle to statusEdit (see GCBO)
% eventdata  reserved
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

end

function versionEdit_Callback(hObject, eventdata, handles)
% hObject    handle to versionEdit (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of versionEdit as text
%        str2double(get(hObject,'String')) returns contents of versionEdit as a double

end

% --- Executes during object creation, after setting all properties.
function versionEdit_CreateFcn(hObject, eventdata, handles)
% hObject    handle to versionEdit (see GCBO)
% eventdata  reserved
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

end

% --- Executes on button press in resetBanksToDefaultPushbutton.
function resetBanksToDefaultPushbutton_Callback(hObject, eventdata, handles)
% hObject    handle to resetBanksToDefaultPushbutton (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

answer = questdlg('This will program all 4 banks with default values. Are you sure you want to proceed?', ...
    'Color Question', ...
    'Yes', 'No', 'No')
switch answer,
    case 'No',
        return;
end % switch

end

% --- Executes during object creation, after setting all properties.
function resetBanksToDefaultPushbutton_CreateFcn(hObject, eventdata, handles)
% hObject    handle to resetBanksToDefaultPushbutton (see GCBO)
% eventdata  reserved
% handles    empty - handles not created until after all CreateFcns called

end

% --- Executes on selection change in StandardSettingsPopupmenu.
function StandardSettingsPopupmenu_Callback(hObject, eventdata, handles)
% hObject    handle to StandardSettingsPopupmenu (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

% Hints: contents = get(hObject,'String') returns StandardSettingsPopupmenu contents as cell array
%        contents{get(hObject,'Value')} returns selected item from StandardSettingsPopupmenu


standardSettingsIndex = get(handles.StandardSettingsPopupmenu,'Value');

switch(standardSettingsIndex)
    case(1)
        startValue = 32768; % Linescan
        increment = 0;
    case(2)
        startValue = 28196; % 1X
        increment = 32;
    case(3)
        startValue = 30482; % 2X
        increment = 16;
    case(4)
        startValue = 31625; % 4X
        increment = 8;
    case(5)
        startValue = 32768;
        increment = 0;
    case(6)
        startValue = 31333;
        increment = 5;
    case(7)
        startValue = 30472;
        increment = 8;
    case(8)
        startValue = 31620;
        increment = 4;
end

set(handles.galvanometerStartValueEdit,'String',num2str(startValue));
set(handles.galvanometerIncrementEdit,'String',num2str(increment));
guidata(hObject, handles);
drawnow
pause(1);
galvanometerStartValueEdit_Callback(hObject, eventdata, handles);
pause(1);
galvanometerIncrementEdit_Callback(hObject, eventdata, handles);

end

% --- Executes during object creation, after setting all properties.
function StandardSettingsPopupmenu_CreateFcn(hObject, eventdata, handles)
% hObject    handle to StandardSettingsPopupmenu (see GCBO)
% eventdata  reserved
% handles    empty - handles not created until after all CreateFcns called

% Hint: polygonspeedcontrolcircuitserialinterfacepopupmenu controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

end

% --- Executes on button press in AdvancedDebugInfoPushbutton.
function AdvancedDebugInfoPushbutton_Callback(hObject, eventdata, handles)
% hObject    handle to AdvancedDebugInfoPushbutton (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

serialInterfaceIndex = get(handles.serialInterfacePopupmenu,'Value');
serialInterfaceStrings = get(handles.serialInterfacePopupmenu,'String');
serialInterface = serialInterfaceStrings{serialInterfaceIndex};
s = serial(serialInterface);
global globalSerialBaudRate;
s.BaudRate = globalSerialBaudRate;
global globalSerialTimeout;
s.Timeout = globalSerialTimeout;
fopen(s);

if (s.status == 'open')
    fwrite(s,READ_NUMBER_OF_LINES_FOR_VSYNC);
    numberOfLinesForVSyncBytes = fread(s, 2);
    numberOfLinesForVSync = numberOfLinesForVSyncBytes(1) * 256 + numberOfLinesForVSyncBytes(2);
    sprintf('Number of lines for VSync: %d\n', numberOfLinesForVSync)
    
    pause(1);
    fwrite(s,[WRITE_NUMBER_OF_LINES_FOR_VSYNC, hex2dec('01'), hex2dec('00')]);
    pause(1);
    
    fwrite(s,READ_NUMBER_OF_LINES_FOR_VSYNC);
    numberOfLinesForVSyncBytes = fread(s, 2);
    numberOfLinesForVSync = numberOfLinesForVSyncBytes(1) * 256 + numberOfLinesForVSyncBytes(2);
    sprintf('Number of lines for VSync: %d\n', numberOfLinesForVSync)
    pause(1);
    
    fwrite(s,READ_NUMBER_OF_LINES_PER_FRAME);
    numberOfLinesBytes = fread(s, 2);
    numberOfLines = numberOfLinesBytes(1) * 256 + numberOfLinesBytes(2);
    
    fwrite(s,READ_TMR1_RELOAD);
    TMR1ReloadValueBytes = fread(s, 2);
    TMR1ReloadValue = TMR1ReloadValueBytes(1) * 256 + TMR1ReloadValueBytes(2);
    polygonClockFrequency = 5000000 / (65535 - TMR1ReloadValue);
    sprintf('Number of lines: %d\nTMR1 reload value(polygon speed control):  %d (0x%04X)\npolygonClockFrequency: %f\n', numberOfLines, TMR1ReloadValue, TMR1ReloadValue, polygonClockFrequency)
    
    address = 0;
    command = [READ_EEPROM_ADDRESS address];
    fwrite(s,command); % Read EERPOM address
    EEPROMAddressValue = fread(s, 1);
    sprintf('EEPROM value at %d is %d (0x%02X)\n', address, EEPROMAddressValue, EEPROMAddressValue)
    address = 1;
    command = [READ_EEPROM_ADDRESS address];
    fwrite(s,command); % Read EERPOM address
    EEPROMAddressValue = fread(s, 1);
    sprintf('EEPROM value at %d is %d (0x%02X)\n', address, EEPROMAddressValue, EEPROMAddressValue)
    
    fclose(s);
else
    msgboxModal(['Could not open serial interface ', serialInterface]);
end

delete(s);
clear s;
set(handles.statusEdit,'String','');

end

function [settingsLoadedFromFile] = loadSettingsFromFile(filePrefix, handles)

FilterSpec = '*.mat';
DialogTitle = 'Load settings from file';
global lastFileForSettings;       
DefaultName = lastFileForSettings;

[FileName,PathName,FilterIndex] = uigetfile(FilterSpec,DialogTitle,DefaultName);

if (FilterIndex == 0)
    settingsLoadedFromFile = 0;
    return;
end

try
 %   load(sprintf('%s_settings', filePrefix));
 load([PathName FileName]);
catch error
    % Not a critical error
    disp(error.message);
    settingsLoadedFromFile = 0;
    return;
end

if (exist('serialInterfaceString'))
    restorePopupmenu(serialInterfaceString, handles.serialInterfacePopupmenu);   
end

if (exist('polygonSpeedControlCircuitSerialInterfaceString'))
        restorePopupmenu(polygonSpeedControlCircuitSerialInterfaceString, handles.polygonSpeedControlCircuitSerialInterfacePopupmenu);   
end

if (exist('galvanometerIncrementEditString'))
    set(handles.galvanometerIncrementEdit,'String', galvanometerIncrementEditString);
end

if (exist('galvanometerStartValueEditString'))
    set(handles.galvanometerStartValueEdit,'String', galvanometerStartValueEditString);
end

if (exist('numberOfLinesForVSyncEditString'))
    set(handles.numberOfLinesForVSyncEdit,'String', numberOfLinesForVSyncEditString);
end

if (exist('TMR1ReloadValueEditString'))
    set(handles.TMR1ReloadValueEdit,'String', TMR1ReloadValueEditString);
end

if (exist('numberOfLinesPerFrameEditString'))
    set(handles.numberOfLinesPerFrameEdit,'String', numberOfLinesPerFrameEditString);
end

if (exist('fixedPolygonRevolutionsPerMinuteEditString'))
    set(handles.fixedPolygonRevolutionsPerMinuteEdit,'String', fixedPolygonRevolutionsPerMinuteEditString);    
end

if (exist('polygonSpeedIsFixedCheckboxValue'))   
else
    polygonSpeedIsFixedCheckboxValue = 1;
end

set(handles.polygonSpeedIsFixedCheckbox,'Value', polygonSpeedIsFixedCheckboxValue);

setGUIElementsBasedOnPolygonSpeedFixedOrNot(polygonSpeedIsFixedCheckboxValue, handles);

settingsLoadedFromFile = 1;

end

function flag = isnet()
% This function returns a 1 if basic internet connectivity
% is present and returns a zero if no internet connectivity
% is detected.

% define the URL for US Naval Observatory Time page
% February 9, 2012: the following link was so slow to respond that it
% essentially froze the program.
%url = java.net.URL('http://tycho.usno.navy.mil/cgi-bin/timer.pl');
url = java.net.URL('http://www.google.com');

try 
    % read the URL
    link = openStream(url);
    parse = java.io.InputStreamReader(link);
    snip = java.io.BufferedReader(parse);
    if ~isempty(snip)
        flag = 1;
    else
        flag = 0;
    end    
catch error
    flag = 0;
end

return;

end

function versionComparison = compareVersion(currentVersion, latestVersion)
    versionComparison = 0;

    if (latestVersion(1) > currentVersion(1)) % major
        versionComparison = 1;
    else
        if (latestVersion(1) < currentVersion(1)) % major
            versionComparison = -1;            
        else
            % major versions are equal
            if (latestVersion(2) > currentVersion(2)) % minor
                versionComparison = 1;
            else
                if (latestVersion(2) < currentVersion(2)) % minor
                    versionComparison = -1;                    
                else
                    % minor versions are equal
                    if (latestVersion(3) > currentVersion(3)) % trivial
                        versionComparison = 1;
                    else
                        if (latestVersion(3) < currentVersion(3)) % trivial
                            versionComparison = -1;
                        else
                            % trivial versions are equal
                            versionComparison = 0;                            
                        end
                    end
                end
            end
        end
    end   
end


% --- Executes on button press in userManualPushbutton.
function userManualPushbutton_Callback(hObject, eventdata, handles)
% hObject    handle to userManualPushbutton (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

fetchOnlineUserManual(hObject, eventdata, handles);

end

function fetchOnlineUserManual(hObject, eventdata, handles)

    selectedCircuitPopupmenu = handles.selectedCircuitPopupmenu;    
    selectedCircuitIndex = get(selectedCircuitPopupmenu,'Value');
    selectedCircuitStrings = get(selectedCircuitPopupmenu,'String');
    selectedCircuit = selectedCircuitStrings{selectedCircuitIndex};
    if (selectedCircuitIndex == 2)
        userManualURL = 'https://docs.google.com/document/d/1YBuvefDFxHnAYsUo5FYOtOlqaJsFZ-M2dQw85Boi_gc/edit?hl=en_US';
    else
        userManualURL = 'https://docs.google.com/document/d/12TKeQJD8Tolzk7SCWUknGBu3tH7U27PAxt9wRvmOMP4/edit?hl=en_US';
    end    

    web(userManualURL, '-browser');

end

% --- Executes on button press in getCIDPushbutton.
function [error] = getCIDPushbutton_Callback(hObject, eventdata, handles)
% hObject    handle to getCIDPushbutton (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

error = 0; %default.

set(handles.CIDEdit,'String','Unknown');
set(handles.statusEdit,'String','Getting CID...');
drawnow

expectedNumberOfBytes = 2;
bytesReturned = sendSerialPrimitiveAndWaitForBytes(handles, READ_CID, expectedNumberOfBytes);
if (numel(bytesReturned) < expectedNumberOfBytes)
    errorDialogAndStatus('Error: could not get the expected number of bytes (2) while reading CID.', mfilename, handles);
    error = 1;
    return;    
end

set(handles.CIDEdit,'String',num2str(bytesReturned(1) * 256 + bytesReturned(2)));
set(handles.statusEdit,'String','');

end

% --- Executes on button press in getCPNPushbutton.
function [error CPN] = getCPNPushbutton_Callback(hObject, eventdata, handles, forcedSelectedCircuitIndex)
% hObject    handle to getCPNPushbutton (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

error = 0; %default.

set(handles.CPNEdit,'String','Unknown');
set(handles.statusEdit,'String','Getting CPN...');
drawnow

expectedNumberOfBytes = 2;
if (exist('forcedSelectedCircuitIndex'))
    bytesReturned = sendSerialPrimitiveAndWaitForBytes(handles, READ_CPN, expectedNumberOfBytes, forcedSelectedCircuitIndex);
else
     bytesReturned = sendSerialPrimitiveAndWaitForBytes(handles, READ_CPN, expectedNumberOfBytes);
end
if (numel(bytesReturned) < expectedNumberOfBytes)
    errorDialogAndStatus('Error: could not get the expected number of bytes (2) while reading CPN.', mfilename, handles);
    error = 1;
    return;    
end
CPN = bytesReturned(1) * 256 + bytesReturned(2);
if (exist('forcedSelectedCircuitIndex'))
    set(handles.CPNEdit,'String','Unknown');
else
    set(handles.CPNEdit,'String',num2str(CPN));
end

set(handles.statusEdit,'String','');


selectedCircuitPopupmenu = handles.selectedCircuitPopupmenu;
if (exist('forcedSelectedCircuitIndex'))
    selectedCircuitIndex = forcedSelectedCircuitIndex;
else
    selectedCircuitIndex = get(selectedCircuitPopupmenu,'Value');
end
selectedCircuitStrings = get(selectedCircuitPopupmenu,'String');
selectedCircuit = selectedCircuitStrings{selectedCircuitIndex};
if (selectedCircuitIndex == 2)
    if (CPN ~= 607)
        msgboxModal('Warning: CPN is not what was expected (607). It may be that you selected the wrong serial port for the polygon speed control circuit or that the wrong firmware was programmed in the circuit.');
    end
else
    % Video rate synchronization circuit
    if (CPN ~= 522)
        msgboxModal('Warning: CPN is not what was expected (522). It may be that you selected the wrong serial port for the video rate synchronization circuit or that the wrong firmware was programmed in the circuit.');
    end
end

end

% --- Executes on button press in getSNPushbutton.
function [error] = getSNPushbutton_Callback(hObject, eventdata, handles)
% hObject    handle to getSNPushbutton (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

error = 0; %default.

set(handles.SNEdit,'String','Unknown');
set(handles.statusEdit,'String','Getting SN...');
drawnow

expectedNumberOfBytes = 2;
bytesReturned = sendSerialPrimitiveAndWaitForBytes(handles, READ_SN, expectedNumberOfBytes);
if (numel(bytesReturned) < expectedNumberOfBytes)
    errorDialogAndStatus('Error: could not get the expected number of bytes (2) while reading SN.', mfilename, handles);
    error = 1;
    return;
end

set(handles.SNEdit,'String',num2str(bytesReturned(1) * 256 + bytesReturned(2)));
set(handles.statusEdit,'String','');

end

function errorDialogAndStatus(message, title, handles)

uiwait(errordlg(message, title, 'modal'));

if (exist('handles'))
    set(handles.statusEdit,'String', message);
end
end

function CIDEdit_Callback(hObject, eventdata, handles)
% hObject    handle to CIDEdit (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of CIDEdit as text
%        str2double(get(hObject,'String')) returns contents of CIDEdit as a double

end

% --- Executes during object creation, after setting all properties.
function CIDEdit_CreateFcn(hObject, eventdata, handles)
% hObject    handle to CIDEdit (see GCBO)
% eventdata  reserved
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

end

function CPNEdit_Callback(hObject, eventdata, handles)
% hObject    handle to CPNEdit (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of CPNEdit as text
%        str2double(get(hObject,'String')) returns contents of CPNEdit as a double

end

% --- Executes during object creation, after setting all properties.
function CPNEdit_CreateFcn(hObject, eventdata, handles)
% hObject    handle to CPNEdit (see GCBO)
% eventdata  reserved
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

end

function SNEdit_Callback(hObject, eventdata, handles)
% hObject    handle to SNEdit (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of SNEdit as text
%        str2double(get(hObject,'String')) returns contents of SNEdit as a double

end

% --- Executes during object creation, after setting all properties.
function SNEdit_CreateFcn(hObject, eventdata, handles)
% hObject    handle to SNEdit (see GCBO)
% eventdata  reserved
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

end

function [bytesReturned] = sendSerialPrimitiveAndWaitForBytes(handles, primitive, expectedNumberOfBytes, forcedSelectedCircuitIndex)

global globalPolygonClockIsDisable;
global globalTMR1ReloadValue; 
global globalNumberOfLinesPerFrame;
global globalDACIncrement;
global globalDACStart;
global globalNumberOfLinesForVSync;
global globalSendSerialPrimitiveAndWaitForBytesReverseLog;

primitive

selectedCircuitPopupmenu = handles.selectedCircuitPopupmenu;
if (exist('forcedSelectedCircuitIndex'))
    selectedCircuitIndex = forcedSelectedCircuitIndex;
else
    selectedCircuitIndex = get(selectedCircuitPopupmenu,'Value');
end
selectedCircuitStrings = get(selectedCircuitPopupmenu,'String');
selectedCircuit = selectedCircuitStrings{selectedCircuitIndex}; 

if ((primitive(1) == READ_FIRMWARE_VERSION) ...
    || (primitive(1) == READ_CID) ...
    || (primitive(1) == READ_CPN) ...
    || (primitive(1) == READ_SN) ...
    || (primitive(1) == READ_BUILD_DATE) ...
    || (primitive(1) == LOAD_SETTINGS_FROM_PRESET_BANK) ...
    || (primitive(1) == WRITE_SETTINGS_TO_PRESET_BANK) ...
    || (primitive(1) == READ_STATE_OF_SWITCHES_AND_TTL_IOS) ...    
    || (primitive(1) == READ_BUILD_TIME))
    if (selectedCircuitIndex == 2)        
        serialInterfacePopupmenu = handles.polygonSpeedControlCircuitSerialInterfacePopupmenu;                               
    else    
        % Video rate synchronization circuit
        serialInterfacePopupmenu = handles.serialInterfacePopupmenu;
    end
        
elseif ((primitive(1) == WRITE_TMR1_RELOAD) ...
        || (primitive(1) == READ_TMR1_RELOAD) ...
        || (primitive(1) == DISABLE_POLYGON_CLOCK) ...
        || (primitive(1) == ENABLE_POLYGON_CLOCK) ...
        )
    % For primitives these primitives, we use the
    % polygon speed control serial interface, which by the way used to be the
    % same as the video rate synchronization circuit but this last case is
    % to be avoided.
    serialInterfacePopupmenu = handles.polygonSpeedControlCircuitSerialInterfacePopupmenu;
else
    serialInterfacePopupmenu = handles.serialInterfacePopupmenu;
end
serialInterfaceIndex = get(serialInterfacePopupmenu,'Value');
serialInterfaceStrings = get(serialInterfacePopupmenu,'String');
serialInterface = serialInterfaceStrings{serialInterfaceIndex};

% Latest primitive comes first so that if we have to truncate, we do not
% lose the most relevant debug information.

thisLog = sprintf(' %02X', serialInterfaceIndex);
for (i = 1:length(primitive))
    thisLog = strcat(thisLog, sprintf('%02X', primitive(i)));    
end

globalSendSerialPrimitiveAndWaitForBytesReverseLog = strcat(thisLog, globalSendSerialPrimitiveAndWaitForBytesReverseLog);    

debug(sprintf('Current length of globalSendSerialPrimitiveAndWaitForBytesReverseLog is %d', length(globalSendSerialPrimitiveAndWaitForBytesReverseLog)));

if (serialInterfaceIndex == length(serialInterfaceStrings)) % Test for last string which is "Emulate"
    % We are in emulation.
    switch primitive(1)
        case READ_FIRMWARE_VERSION
            bytesReturned = [255, 255, 255];
            return;
        case READ_CPN
            if (selectedCircuitIndex == 2)
                bytesReturned = [2, 95]; % 607
            else
                bytesReturned = [2, 10]; % 522
            end
            return;
        case READ_CID
            bytesReturned = [0, 0];
            return;
        case READ_SN
            bytesReturned = [0, 0];
            return;
        case READ_EEPROM_ADDRESS
            bytesReturned = [255];
            return;            
        case SWITCH_TO_BOOTLOADER_MODE
            disp('Debug: device would have switched to bootloader mode if supported.');
            return;            
        case READ_STATE_OF_SWITCHES_AND_TTL_IOS
            bytesReturned = 0;
            return;
        case WRITE_SETTINGS_TO_PRESET_BANK
            bytesReturned = 0;
            return;
        case LOAD_SETTINGS_FROM_PRESET_BANK
            bytesReturned = 0;
            return;            
        case READ_BUILD_TIME
            bytesReturned = ['0' '0' ':' '0' '0' ':' '0' '0' 0];
            %__TIME__   HOUR:MIN:SEC    "23:59:59" (length is 8 + 1 null)
            return;            
        case READ_BUILD_DATE
            bytesReturned = ['J' 'a' 'n' ' ' '1' ' ' '1' '9' '0' '0' 0];
            % __DATE__   MONTH DAY YEAR  "Jan 1 2005" (length is 10 + 1 null)
            return;
    end
    
    %if (selectedCircuitIndex == 2)
    % CPN607 is for RS-232 programmable TTL frequency generator
    switch primitive(1)        
        case DISABLE_POLYGON_CLOCK
            globalPolygonClockIsDisable = 1;
            bytesReturned = 0;
            debug('Emulated DISABLE_POLYGON_CLOCK done.');
            return;            
        case ENABLE_POLYGON_CLOCK            
            globalPolygonClockIsDisable = 0;
            bytesReturned = 0;
            debug('Emulated ENABLE_POLYGON_CLOCK done.');
            return;            
        case WRITE_TMR1_RELOAD
            globalTMR1ReloadValue = uint16(primitive(2)) * 256 + uint16(primitive(3));
            bytesReturned = 0;
            return;            
        case READ_TMR1_RELOAD
            TMR1ReloadValueMostSignificantByte = uint8(bitshift(globalTMR1ReloadValue, -8));
            TMR1ReloadValueLeastSignificantByte = rem(globalTMR1ReloadValue, 256);
            bytesReturned = [uint16(TMR1ReloadValueMostSignificantByte) uint16(TMR1ReloadValueLeastSignificantByte)];
            return;
    end
    %else
    % CPN522 is for Blanker six-channel multiplexer and video rate synchronization circuit
    
    switch primitive(1)        
        case WRITE_NUMBER_OF_LINES_PER_FRAME
            globalNumberOfLinesPerFrame = uint16(primitive(2)) * 256 + uint16(primitive(3));
            bytesReturned = 0;
            return;            
        case WRITE_DAC_START
            globalDACStart = uint16(primitive(2)) * 256 + uint16(primitive(3));
            bytesReturned = 0;
            return;
        case WRITE_DAC_INCREMENT
            globalDACIncrement = uint16(primitive(2)) * 256 + uint16(primitive(3));
            bytesReturned = 0;
            return;
        case READ_NUMBER_OF_LINES_PER_FRAME
            numberOfLinesPerFrameMostSignificantByte = uint8(bitshift(globalNumberOfLinesPerFrame, -8));
            numberOfLinesPerFrameLeastSignificantByte = rem(globalNumberOfLinesPerFrame, 256);
            bytesReturned = [uint16(numberOfLinesPerFrameMostSignificantByte) uint16(numberOfLinesPerFrameLeastSignificantByte)];
            return;
        case READ_DAC_START
            DACStartMostSignificantByte = uint8(bitshift(globalDACStart, -8));
            DACStartLeastSignificantByte = rem(globalDACStart, 256);
            bytesReturned = [uint16(DACStartMostSignificantByte) uint16(DACStartLeastSignificantByte)];
            return;
        case READ_DAC_INCREMENT
            DACIncrementMostSignificantByte = uint8(bitshift(globalDACIncrement, -8));
            DACIncrementLeastSignificantByte = rem(globalDACIncrement, 256);
            bytesReturned = [uint16(DACIncrementMostSignificantByte) uint16(DACIncrementLeastSignificantByte)];
            return;
        case READ_NUMBER_OF_LINES_FOR_VSYNC
            numberOfLinesForVSyncMostSignificantByte = uint8(bitshift(globalNumberOfLinesForVSync, -8));
            numberOfLinesForVSyncLeastSignificantByte = rem(globalNumberOfLinesForVSync, 256);
            bytesReturned = [uint16(numberOfLinesForVSyncMostSignificantByte) uint16(numberOfLinesForVSyncLeastSignificantByte)];
            return;            
        case WRITE_NUMBER_OF_LINES_FOR_VSYNC
            globalNumberOfLinesForVSync = uint16(primitive(2)) * 256 + uint16(primitive(3));
            bytesReturned = 0;
            return;
    end
    %end
    bytesReturned = -1;
    return;
end
                 
s = serial(serialInterface);
global globalSerialBaudRate;
s.BaudRate = globalSerialBaudRate;
global globalSerialTimeout;
s.Timeout = globalSerialTimeout;
fopen(s);

if (s.status == 'open')
    fwrite(s, primitive);
    if (expectedNumberOfBytes > 0)        
        bytesReturned = fread(s, expectedNumberOfBytes);        
        debug(sprintf('sendSerialPrimitiveAndWaitForBytes: fread returned %d', numel(bytesReturned)));
    else
        bytesReturned = -2;
    end
    fclose(s);
else    
    msgboxModal(['Could not open serial interface ', serialInterface]);
    bytesReturned = -1;
end

delete(s);
clear s;

end


% --- Executes on button press in writeSettingsToFilePushbutton.
function writeSettingsToFilePushbutton_Callback(hObject, eventdata, handles)
% hObject    handle to writeSettingsToFilePushbutton (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

FilterSpec = '*.mat';
DialogTitle = mfilename;
global lastFileForSettings;       
DefaultName = lastFileForSettings;

[FileName,PathName,FilterIndex] = uiputfile(FilterSpec, DialogTitle, DefaultName);

if (FilterIndex == 0)
    return;
end

serialInterfaceStrings = get(handles.serialInterfacePopupmenu,'String');
serialInterfaceString = serialInterfaceStrings(get(handles.serialInterfacePopupmenu,'Value'));

polygonSpeedControlCircuitSerialInterfaceStrings = get(handles.polygonSpeedControlCircuitSerialInterfacePopupmenu,'String');
polygonSpeedControlCircuitSerialInterfaceString = serialInterfaceStrings(get(handles.polygonSpeedControlCircuitSerialInterfacePopupmenu,'Value'));

galvanometerStartValueEditString = get(handles.galvanometerStartValueEdit, 'String');
galvanometerIncrementEditString = get(handles.galvanometerIncrementEdit, 'String');
numberOfLinesPerFrameEditString = get(handles.numberOfLinesPerFrameEdit, 'String');
numberOfLinesForVSyncEditString = get(handles.numberOfLinesForVSyncEdit, 'String');
TMR1ReloadValueEditString = get(handles.TMR1ReloadValueEdit, 'String');
fixedPolygonRevolutionsPerMinuteEditString = get(handles.fixedPolygonRevolutionsPerMinuteEdit, 'String');
polygonSpeedIsFixedCheckboxValue = get(handles.polygonSpeedIsFixedCheckbox, 'Value');

save ([PathName FileName], 'serialInterfaceString', ...
    'galvanometerStartValueEditString', 'galvanometerIncrementEditString', ...
    'numberOfLinesPerFrameEditString', 'numberOfLinesForVSyncEditString', ...
    'polygonSpeedControlCircuitSerialInterfaceString', ...    
    'TMR1ReloadValueEditString', ...
    'fixedPolygonRevolutionsPerMinuteEditString', ...
    'polygonSpeedIsFixedCheckboxValue');

lastFileForSettings = [PathName FileName];
end

% --- Executes on button press in loadSettingsFromFilePushbutton.
function loadSettingsFromFilePushbutton_Callback(hObject, eventdata, handles)
% hObject    handle to loadSettingsFromFilePushbutton (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

loadSettingsFromFile(mfilename, handles);

if (get(handles.writeSettingsToCircuitsAfterLoadingFromFileCheckbox, 'Value') == 1)
    writeSettingsToCircuitPushbutton_Callback(hObject, eventdata, handles);
end

end

% --- Executes on button press in writeSettingsToCircuitPushbutton.
function writeSettingsToCircuitPushbutton_Callback(hObject, eventdata, handles)
% hObject    handle to writeSettingsToCircuitPushbutton (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

galvanometerStartValueEdit_Callback(handles.galvanometerStartValueEdit, eventdata, handles);
galvanometerIncrementEdit_Callback(handles.galvanometerIncrementEdit, eventdata, handles);
numberOfLinesPerFrameEdit_Callback(handles.numberOfLinesPerFrameEdit, eventdata, handles);
numberOfLinesForVSyncEdit_Callback(handles.numberOfLinesForVSyncEdit, eventdata, handles);
TMR1ReloadValueEdit_Callback(handles.TMR1ReloadValueEdit, eventdata, handles);

end

% --- Executes on button press in loadSettingsFromCircuitPushbutton.
function loadSettingsFromCircuitPushbutton_Callback(hObject, eventdata, handles)
% hObject    handle to loadSettingsFromCircuitPushbutton (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)


readStartValuePushbutton_Callback(handles.readStartValuePushbutton, eventdata, handles);
readIncrementPushbutton_Callback(handles.readIncrementPushbutton, eventdata, handles);
readNumberOfLinesPerFramePushbutton_Callback(handles.readNumberOfLinesPerFramePushbutton, eventdata, handles);
readNumberOfLinesForVSyncPushbutton_Callback(handles.readNumberOfLinesForVSyncPushbutton, eventdata, handles);
readTMR1ReloadValuePushbutton_Callback(handles.readTMR1ReloadValuePushbutton, eventdata, handles);

end

function restorePopupmenu(stringToSet, handleForPopupmenu)

    strings = get(handleForPopupmenu,'String');

    for i = 1:size(strings, 1)
        if (strcmp(strings(i), stringToSet))
            % Using UserData to pass a message to callback so that circuit
            % does not get updated.
            set(handleForPopupmenu,'UserData', 0);
            set(handleForPopupmenu,'Value', i);
            set(handleForPopupmenu,'UserData', 1);
            break;
        end
    end


end

function numberOfLinesForVSyncEdit_Callback(hObject, eventdata, handles)
% hObject    handle to numberOfLinesForVSyncEdit (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of numberOfLinesForVSyncEdit as text
%        str2double(get(hObject,'String')) returns contents of numberOfLinesForVSyncEdit as a double

numberOfLinesForVSyncString = get(handles.numberOfLinesForVSyncEdit,'String');

if (isempty(numberOfLinesForVSyncString))
   msgboxModal('Set number of lines for VSync first.');
   return;
end

numberOfLinesForVSync = str2num(numberOfLinesForVSyncString);

if (numberOfLinesForVSync < 1 || numberOfLinesForVSync > 575)
    msgboxModal('Number of lines for VSync is outside valid range, i.e. 1 to 575');
    return    
end

set(handles.statusEdit,'String', 'Writing number of lines for VSync...');
drawnow

numberOfLinesForVSyncMostSignificantByte = uint8(floor(numberOfLinesForVSync / 256));
numberOfLinesForVSyncLeastSignificantByte = rem(numberOfLinesForVSync, 256);

bytesReturned = sendSerialPrimitiveAndWaitForBytes(handles, [WRITE_NUMBER_OF_LINES_FOR_VSYNC uint8(numberOfLinesForVSyncMostSignificantByte) uint8(numberOfLinesForVSyncLeastSignificantByte)], 0);

if (bytesReturned == -1)
    msgboxModal('Error: Could not change number of lines for VSync.');    
end

set(handles.statusEdit,'String','');
drawnow

end


% --- Executes during object creation, after setting all properties.
function numberOfLinesForVSyncEdit_CreateFcn(hObject, eventdata, handles)
% hObject    handle to numberOfLinesForVSyncEdit (see GCBO)
% eventdata  reserved
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

end

% --- Executes on button press in readNumberOfLinesForVSyncPushbutton.
function readNumberOfLinesForVSyncPushbutton_Callback(hObject, eventdata, handles)
% hObject    handle to readNumberOfLinesForVSyncPushbutton (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

set(handles.statusEdit,'String','Reading number of lines for VSync...');
drawnow

bytesReturned = sendSerialPrimitiveAndWaitForBytes(handles, READ_NUMBER_OF_LINES_FOR_VSYNC, 2);

if (isempty(bytesReturned))
    msgboxModal('Error: Could not change number of lines for VSync.');
else
    numberOfLinesForVSyncString = [num2str(bytesReturned(1) * 256 + bytesReturned(2))];
    % need to convert the answer back into String type to display it
    set(handles.numberOfLinesForVSyncEdit,'String', numberOfLinesForVSyncString);
    
end

set(handles.statusEdit,'String','');

end



function numberOfLinesPerFrameEdit_Callback(hObject, eventdata, handles)
% hObject    handle to numberOfLinesPerFrameEdit (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of numberOfLinesPerFrameEdit as text
%        str2double(get(hObject,'String')) returns contents of numberOfLinesPerFrameEdit as a double


numberOfLinesPerFrameString = get(handles.numberOfLinesPerFrameEdit,'String');

if (isempty(numberOfLinesPerFrameString))
   msgboxModal('Set number of lines per frame first.');
   return;
end

numberOfLinesPerFrame = str2num(numberOfLinesPerFrameString);

if (numberOfLinesPerFrame < 36 || numberOfLinesPerFrame > 65520)
    ('Number of lines per frame is outside valid range, i.e. 36 to 65520');
    return    
end

if (rem(numberOfLinesPerFrame, 36) ~= 0)
    remainder = rem(numberOfLinesPerFrame, 36);
    msgboxModal(sprintf('Number of lines per frame must be a multiple of 36. Closest values are %d and %d', numberOfLinesPerFrame - remainder, numberOfLinesPerFrame - remainder + 36));
    return    
end

set(handles.statusEdit,'String', 'Writing number of lines per frame...');
drawnow

numberOfLinesPerFrameMostSignificantByte = uint8(floor(numberOfLinesPerFrame / 256));
numberOfLinesPerFrameLeastSignificantByte = rem(numberOfLinesPerFrame, 256);

bytesReturned = sendSerialPrimitiveAndWaitForBytes(handles, [WRITE_NUMBER_OF_LINES_PER_FRAME uint8(numberOfLinesPerFrameMostSignificantByte) uint8(numberOfLinesPerFrameLeastSignificantByte)], 0);

if (bytesReturned == -1)
    msgboxModal('Error: Could not change number of lines per frame.');    
end

set(handles.statusEdit,'String','');
drawnow

%computeRatesDeprecated(hObject, eventdata, handles);

end

% --- Executes during object creation, after setting all properties.
function numberOfLinesPerFrameEdit_CreateFcn(hObject, eventdata, handles)
% hObject    handle to numberOfLinesPerFrameEdit (see GCBO)
% eventdata  reserved
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

end

% --- Executes on button press in readNumberOfLinesPerFramePushbutton.
function readNumberOfLinesPerFramePushbutton_Callback(hObject, eventdata, handles)
% hObject    handle to readNumberOfLinesPerFramePushbutton (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

set(handles.statusEdit,'String','Reading number of lines per frame...');
drawnow

bytesReturned = sendSerialPrimitiveAndWaitForBytes(handles, READ_NUMBER_OF_LINES_PER_FRAME, 2);

if (isempty(bytesReturned))
    msgboxModal('Error: Could not read number of lines per frame.');    
else
    numberOfLinesPerFrameString = [num2str(bytesReturned(1) * 256 + bytesReturned(2))];
    % need to convert the answer back into String type to display it
    set(handles.numberOfLinesPerFrameEdit,'String', numberOfLinesPerFrameString);
end

set(handles.statusEdit,'String','');

end


% --- Executes on selection change in polygonSpeedControlCircuitSerialInterfacePopupmenu.
function polygonSpeedControlCircuitSerialInterfacePopupmenu_Callback(hObject, eventdata, handles)
% hObject    handle to polygonSpeedControlCircuitSerialInterfacePopupmenu (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

% Hints: contents = cellstr(get(hObject,'String')) returns polygonSpeedControlCircuitSerialInterfacePopupmenu contents as cell array
%        contents{get(hObject,'Value')} returns selected item from polygonSpeedControlCircuitSerialInterfacePopupmenu

end

% --- Executes during object creation, after setting all properties.
function polygonSpeedControlCircuitSerialInterfacePopupmenu_CreateFcn(hObject, eventdata, handles)
% hObject    handle to polygonSpeedControlCircuitSerialInterfacePopupmenu (see GCBO)
% eventdata  reserved
% handles    empty - handles not created until after all CreateFcns called

% Hint: polygonspeedcontrolcircuitserialinterfacepopupmenu controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

end



function TMR1ReloadValueEdit_Callback(hObject, eventdata, handles)
% hObject    handle to TMR1ReloadValueEdit (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of TMR1ReloadValueEdit as text
%        str2double(get(hObject,'String')) returns contents of TMR1ReloadValueEdit as a double


TMR1ReloadValueString = get(handles.TMR1ReloadValueEdit,'String');

if (isempty(TMR1ReloadValueString))
   msgboxModal('Set TMR1 reload value first.');
   return;
end

TMR1ReloadValue = str2num(TMR1ReloadValueString);

TMR1ReloadValueMinimum = 40535;
TMR1ReloadValueMaximum = 60327;
if (TMR1ReloadValue < TMR1ReloadValueMinimum  || TMR1ReloadValue > TMR1ReloadValueMaximum)
    errorMessageString = sprintf('TMR1 reload value is outside valid range, i.e. %d to %d.', TMR1ReloadValueMinimum, TMR1ReloadValueMaximum);
    msgboxModal(errorMessageString);
    return;    
end

set(handles.statusEdit,'String', 'Writing TMR1 reload value...');
drawnow

% computeRatesDeprecated(hObject, eventdata, handles);

TMR1ReloadValueMostSignificantByte = uint8(floor(TMR1ReloadValue / 256));
TMR1ReloadValueLeastSignificantByte = rem(TMR1ReloadValue, 256);

bytesReturned = sendSerialPrimitiveAndWaitForBytes(handles, [WRITE_TMR1_RELOAD uint8(TMR1ReloadValueMostSignificantByte) uint8(TMR1ReloadValueLeastSignificantByte)], 0);

if (bytesReturned == -1)
    msgboxModal('Error: Could not change TMR1 reload value.');    
end

set(handles.statusEdit,'String','');
drawnow

end

% --- Executes during object creation, after setting all properties.
function TMR1ReloadValueEdit_CreateFcn(hObject, eventdata, handles)
% hObject    handle to TMR1ReloadValueEdit (see GCBO)
% eventdata  reserved
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

end

function [polygonRevolutionsPerMinute] = computePolygonRevolutionsPerMinute(polygonClockFrequency)
    polygonRevolutionsPerMinute = polygonClockFrequency / 2 * 60;
end

function [HSyncFrequency] = computeHSyncFrequency(polygonRevolutionsPerMinute)

numberOfFacesOfPolygon = 36;

HSyncFrequency = polygonRevolutionsPerMinute * numberOfFacesOfPolygon;

end

function [pixelFrequency HSyncFrequency] = computeRates(iPhotonNumberOfPixelsPerLine, polygonRevolutionsPerMinute)

numberOfFacesOfPolygon = 36;

HSyncFrequency = polygonRevolutionsPerMinute / 60 * numberOfFacesOfPolygon;

pixelFrequency = iPhotonNumberOfPixelsPerLine * HSyncFrequency;

end

function [pixelFrequency] = computePixelFrequency(iPhotonNumberOfPixelsPerLine, polygonRevolutionsPerMinute)

numberOfFacesOfPolygon = 36;

HSyncFrequency = polygonRevolutionsPerMinute * numberOfFacesOfPolygon;

pixelFrequency = iPhotonNumberOfPixelsPerLine * HSyncFrequency;

end

function [pixelFrequencyIsOK pixelFrequency] = sanityCheckOnPixelFrequency(iPhotonNumberOfPixelsPerLine, polygonRevolutionsPerMinute)

pixelFrequency = computePixelFrequency(iPhotonNumberOfPixelsPerLine, polygonRevolutionsPerMinute);

maximumPixelFrequency = 20e6;

if (pixelFrequency > maximumPixelFrequency)    
    pixelFrequencyIsOK = 1;  
else
    pixelFrequencyIsOK = 0;        
end

end

function computeRatesDeprecated(hObject, eventdata, handles)

debug('computeRatesDeprecated is called.');

TMR1ReloadValueString = get(handles.TMR1ReloadValueEdit, 'String');
if isempty(TMR1ReloadValueString)
   return; 
end
TMR1ReloadValue = str2num(TMR1ReloadValueString);

polygonSpeedIsFixed = get(handles.polygonSpeedIsFixedCheckbox, 'Value');

if (polygonSpeedIsFixed)
    fixedPolygonRevolutionsPerMinuteString = get(handles.fixedPolygonRevolutionsPerMinuteEdit, 'String');    
    fixedPolygonRevolutionsPerMinute = str2num(fixedPolygonRevolutionsPerMinuteString);
    polygonClockFrequency = fixedPolygonRevolutionsPerMinute / 60 * 2;
else
    polygonClockFrequency = 5000000 / (65535 - TMR1ReloadValue);
end

% TBD for / 2 (a jumper???)
%HSyncFrequency = polygonClockFrequency * 36 / 2;

readNumberOfLinesPerFramePushbutton_Callback(handles.readNumberOfLinesPerFramePushbutton, eventdata, handles);
numberOfLinesPerFrameString = get(handles.numberOfLinesPerFrameEdit, 'String');
numberOfLinesPerFrame = str2num(numberOfLinesPerFrameString);

[pixelFrequency HSyncFrequency] = computeRates(iPhotonNumberOfPixelsPerLine, polygonRevolutionsPerMinute);

VSyncFrequency = HSyncFrequency / numberOfLinesPerFrame;

iPhotonNumberOfPixelsPerLineString = get(handles.iPhotonNumberOfPixelsPerLineEdit, 'String');

minimumiPhotonNumberOfPixelsSupported = 1;
maximumiPhotonNumberOfPixelsSupported = 262144;

iPhotonNumberOfPixelsPerLineIsValid = 0;
while (not(iPhotonNumberOfPixelsPerLineIsValid))    
    if strcmp(iPhotonNumberOfPixelsPerLineString, '')
        prompt = {sprintf(['Provide the total pixels per line as set in iPhoton so that a sanity check on the pixel frequency can be computed (in iPhotonRT, Menu Tools -> Show Acquisition Settings -> Total pixels per line).\n\n' ...
        'Note that the Snapper-PCI-24 card supports a range of %d to %d pixels per line but the version of iPhoton used may not support such a wide range. ' ...
        'iPhotonRT 1.1 beta14 has an upper limit of 2048 pixels and a variable lower limit depending on other settings.\n'], minimumiPhotonNumberOfPixelsSupported, maximumiPhotonNumberOfPixelsSupported)};

        numlines=1;
        defaultanswer = {iPhotonNumberOfPixelsPerLineString};

        answer = inputdlg(prompt, mfilename, numlines, defaultanswer);

        if (isempty(answer))
           % User hit cancel.
           return;
        end

        iPhotonNumberOfPixelsPerLineString = char(answer{1});
    end
    if (isempty(iPhotonNumberOfPixelsPerLineString))
        iPhotonNumberOfPixelsPerLineString = '';
        continue;
    end
    
    iPhotonNumberOfPixelsPerLine = str2num(iPhotonNumberOfPixelsPerLineString);
        
    if ((iPhotonNumberOfPixelsPerLine < minimumiPhotonNumberOfPixelsSupported) ...
        || (iPhotonNumberOfPixelsPerLine > maximumiPhotonNumberOfPixelsSupported))
        msgboxModal(sprintf('Error: iPhoton number of pixels per line is outside the valid range of %d to %d.', minimumiPhotonNumberOfPixelsSupported, maximumiPhotonNumberOfPixelsSupported));   
        iPhotonNumberOfPixelsPerLineString = '';
        continue;
    end
    iPhotonNumberOfPixelsPerLineIsValid = 1;
end

set(handles.iPhotonNumberOfPixelsPerLineEdit, 'String', iPhotonNumberOfPixelsPerLineString);

pixelFrequency = computeRates(iPhotonNumberOfPixelsPerLine, polygonClockFrequency);

ratesString = sprintf('Polygon clock: %0.1f Hz, HSync: %0.0f Hz, VSync %0.1f Hz, pixel frequency %0.2e Hz', polygonClockFrequency, HSyncFrequency, VSyncFrequency, pixelFrequency);
set(handles.ratesEdit,'String', ratesString);

if (pixelFrequency > 20e6)
    HSyncFrequencyToHaveBarely20MegaPixelsPerSecond = 20e6 / iPhotonNumberOfPixelsPerLine;
    polygonClockFrequencyToHaveBarely20MegaPixelsPerSecond = HSyncFrequencyToHaveBarely20MegaPixelsPerSecond * 2 / 36;
    TMR1ReloadValueToHaveBarely20MegaPixelsPerSecond = 65535 - (5000000 / polygonClockFrequencyToHaveBarely20MegaPixelsPerSecond);
    fixedPolygonRPMToHaveBarely20MegaPixelsPerSecond = polygonClockFrequencyToHaveBarely20MegaPixelsPerSecond * 60 /2;     
    
    errorMessage = sprintf('Error: at %0.2e MHz, the Snapper-PCI-24 pixel frequency exceeds the maximum allowed of 20 MHz.', pixelFrequency / 1e6);

    if (polygonSpeedIsFixed)
        errorMessage = strcat(errorMessage, sprintf(' To solve this you may want to set the jumpers on the polygon controller to have %d RPM or less.', fixedPolygonRPMToHaveBarely20MegaPixelsPerSecond));
        answer = questdlg(errorMessage, 'Error', 'OK', 'OK');
    else
        errorMessage = strcat(errorMessage, sprintf(' To solve this you may want to set the TMR1ReloadValue to %d', TMR1ReloadValueToHaveBarely20MegaPixelsPerSecond));        
        answer = questdlg(errorMessage, 'Error', 'OK', 'Change it for me', 'Change it for me');
        if strcmp(answer, 'Change it for me')
            set(handles.TMR1ReloadValueEdit,'String', sprintf('%d', TMR1ReloadValueToHaveBarely20MegaPixelsPerSecond));
            TMR1ReloadValueEdit_Callback(hObject, eventdata, handles);
        end
        
    end
end

end

% --- Executes on button press in readTMR1ReloadValuePushbutton.
function readTMR1ReloadValuePushbutton_Callback(hObject, eventdata, handles)
% hObject    handle to readTMR1ReloadValuePushbutton (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

set(handles.statusEdit,'String','Reading TMR1 reload value...');
drawnow

bytesReturned = sendSerialPrimitiveAndWaitForBytes(handles, READ_TMR1_RELOAD, 2);

if (isempty(bytesReturned))
    msgboxModal('Error: Could not read TMR1 reload value.');
else
    TMR1ReloadValue = bytesReturned(1) * 256 + bytesReturned(2);
    TMR1ReloadValueString = num2str(TMR1ReloadValue);
    % need to convert the answer back into String type to display it
    set(handles.TMR1ReloadValueEdit,'String', TMR1ReloadValueString);
    % computeRatesDeprecated(hObject, eventdata, handles);    
end

set(handles.statusEdit,'String','');

end

function ratesEdit_Callback(hObject, eventdata, handles)
% hObject    handle to ratesEdit (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of ratesEdit as text
%        str2double(get(hObject,'String')) returns contents of ratesEdit as a double

end

% --- Executes during object creation, after setting all properties.
function ratesEdit_CreateFcn(hObject, eventdata, handles)
% hObject    handle to ratesEdit (see GCBO)
% eventdata  reserved
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

end


% --- Executes on selection change in selectedCircuitPopupmenu.
function selectedCircuitPopupmenu_Callback(hObject, eventdata, handles)
% hObject    handle to selectedCircuitPopupmenu (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

% Hints: contents = cellstr(get(hObject,'String')) returns selectedCircuitPopupmenu contents as cell array
%        contents{get(hObject,'Value')} returns selected item from selectedCircuitPopupmenu

end

% --- Executes during object creation, after setting all properties.
function selectedCircuitPopupmenu_CreateFcn(hObject, eventdata, handles)
% hObject    handle to selectedCircuitPopupmenu (see GCBO)
% eventdata  reserved
% handles    empty - handles not created until after all CreateFcns called

% Hint: polygonspeedcontrolcircuitserialinterfacepopupmenu controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

end


% --- Executes on selection change in serialInterfacePopupmenu.
function popupmenu6_Callback(hObject, eventdata, handles)
% hObject    handle to serialInterfacePopupmenu (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

% Hints: contents = cellstr(get(hObject,'String')) returns serialInterfacePopupmenu contents as cell array
%        contents{get(hObject,'Value')} returns selected item from serialInterfacePopupmenu

end

% --- Executes during object creation, after setting all properties.
function popupmenu6_CreateFcn(hObject, eventdata, handles)
% hObject    handle to serialInterfacePopupmenu (see GCBO)
% eventdata  reserved
% handles    empty - handles not created until after all CreateFcns called

% Hint: polygonspeedcontrolcircuitserialinterfacepopupmenu controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

end

% --- Executes on selection change in polygonSpeedControlCircuitSerialInterfacePopupmenu.
function Popupmenu_Callback(hObject, eventdata, handles)
% hObject    handle to polygonSpeedControlCircuitSerialInterfacePopupmenu (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

% Hints: contents = cellstr(get(hObject,'String')) returns polygonSpeedControlCircuitSerialInterfacePopupmenu contents as cell array
%        contents{get(hObject,'Value')} returns selected item from polygonSpeedControlCircuitSerialInterfacePopupmenu

end

% --- Executes during object creation, after setting all properties.
function Popupmenu_CreateFcn(hObject, eventdata, handles)
% hObject    handle to polygonSpeedControlCircuitSerialInterfacePopupmenu (see GCBO)
% eventdata  reserved
% handles    empty - handles not created until after all CreateFcns called

% Hint: polygonspeedcontrolcircuitserialinterfacepopupmenu controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

end

function edit15_Callback(hObject, eventdata, handles)
% hObject    handle to galvanometerStartValueEdit (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of galvanometerStartValueEdit as text
%        str2double(get(hObject,'String')) returns contents of galvanometerStartValueEdit as a double

end

% --- Executes during object creation, after setting all properties.
function edit15_CreateFcn(hObject, eventdata, handles)
% hObject    handle to galvanometerStartValueEdit (see GCBO)
% eventdata  reserved
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

end



function iPhotonNumberOfPixelsPerLineEdit_Callback(hObject, eventdata, handles)
% hObject    handle to iPhotonNumberOfPixelsPerLineEdit (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of iPhotonNumberOfPixelsPerLineEdit as text
%        str2double(get(hObject,'String')) returns contents of iPhotonNumberOfPixelsPerLineEdit as a double

%computeRatesDeprecated(hObject, eventdata, handles);

end

% --- Executes during object creation, after setting all properties.
function iPhotonNumberOfPixelsPerLineEdit_CreateFcn(hObject, eventdata, handles)
% hObject    handle to iPhotonNumberOfPixelsPerLineEdit (see GCBO)
% eventdata  reserved
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

end


% --- Executes on button press in getBuildDateAndTimePushbutton.
function getBuildDateAndTimePushbutton_Callback(hObject, eventdata, handles)
% hObject    handle to getBuildDateAndTimePushbutton (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

set(handles.buildDateAndTimeEdit,'String','Unknown');
set(handles.statusEdit,'String','Getting build date and time...');
drawnow


buildDate = sendSerialPrimitiveAndWaitForBytes(handles, READ_BUILD_DATE, 11);

if (isempty(buildDate))
    msgboxModal('Error: could not get build date.');
    set(handles.statusEdit,'String','');
    return;
end

buildTime = sendSerialPrimitiveAndWaitForBytes(handles, READ_BUILD_TIME, 9);

if (isempty(buildTime))
    msgboxModal('Error: could not get build time.');
    set(handles.statusEdit,'String','');
    return;
end

set(handles.buildDateAndTimeEdit,'String', sprintf('%s %s', char(buildDate), char(buildTime)));
set(handles.statusEdit,'String','');

end

function buildDateAndTimeEdit_Callback(hObject, eventdata, handles)
% hObject    handle to buildDateAndTimeEdit (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of buildDateAndTimeEdit as text
%        str2double(get(hObject,'String')) returns contents of buildDateAndTimeEdit as a double

end

% --- Executes during object creation, after setting all properties.
function buildDateAndTimeEdit_CreateFcn(hObject, eventdata, handles)
% hObject    handle to buildDateAndTimeEdit (see GCBO)
% eventdata  reserved
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

end


% --- Executes on button press in getStateOfSwitchesPushbutton.
function getStateOfSwitchesPushbutton_Callback(hObject, eventdata, handles)
% hObject    handle to getStateOfSwitchesPushbutton (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)



error = 0; %default.

set(handles.switchesEdit,'String','Unknown');
set(handles.statusEdit,'String','Getting state of switches...');
drawnow

expectedNumberOfBytes = 1;
bytesReturned = sendSerialPrimitiveAndWaitForBytes(handles, READ_STATE_OF_SWITCHES_AND_TTL_IOS, expectedNumberOfBytes);
if (numel(bytesReturned) < expectedNumberOfBytes)
    errorDialogAndStatus(sprintf('Error: could not get the expected number of bytes (%d) while reading state of switches.', expectedNumberOfBytes), mfilename, handles);
    error = 1;
    return;    
end

% Getting rid of state of TTL I/O' s
stateOfLeftSwitch = bitand(bytesReturned(1),1);
if (stateOfLeftSwitch)
    stateOfLeftSwitchString =  'Left: down ';
else
    stateOfLeftSwitchString =  'Left:  up  ';    
end
stateOfRightSwitch = bitand(bytesReturned(1),2);

if (stateOfRightSwitch)
    stateOfRightSwitchString = 'Right: down';
else
    stateOfRightSwitchString = 'Right: up  ';    
end
set(handles.switchesEdit,'String', [stateOfLeftSwitchString ' ' stateOfRightSwitchString]);
set(handles.statusEdit,'String','');

end

function switchesEdit_Callback(hObject, eventdata, handles)
% hObject    handle to switchesEdit (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of switchesEdit as text
%        str2double(get(hObject,'String')) returns contents of switchesEdit as a double

end

% --- Executes during object creation, after setting all properties.
function switchesEdit_CreateFcn(hObject, eventdata, handles)
% hObject    handle to switchesEdit (see GCBO)
% eventdata  reserved
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

end
% --- Executes when figure1 is resized.
function figure1_ResizeFcn(hObject, eventdata, handles)
% hObject    handle to figure1 (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)
end


% --- Executes on selection change in TMR1PresetsPopupmenu.
function TMR1PresetsPopupmenu_Callback(hObject, eventdata, handles)
% hObject    handle to TMR1PresetsPopupmenu (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

% Hints: contents = cellstr(get(hObject,'String')) returns TMR1PresetsPopupmenu contents as cell array
%        contents{get(hObject,'Value')} returns selected item from TMR1PresetsPopupmenu

TMR1PresetsIndex = get(handles.TMR1PresetsPopupmenu,'Value');

switch(TMR1PresetsIndex)
    case(1)
        TMR1ReloadValue = 60327; % 100 % maximum polygon speed
    case(2)
        TMR1ReloadValue = 55119; % 50 % maximum polygon speed       
end

set(handles.TMR1ReloadValueEdit,'String',num2str(TMR1ReloadValue));
guidata(hObject, handles);
drawnow
pause(1);
TMR1ReloadValueEdit_Callback(hObject, eventdata, handles);

end

% --- Executes during object creation, after setting all properties.
function TMR1PresetsPopupmenu_CreateFcn(hObject, eventdata, handles)
% hObject    handle to TMR1PresetsPopupmenu (see GCBO)
% eventdata  reserved
% handles    empty - handles not created until after all CreateFcns called

% Hint: popupmenu controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

end


% --- Executes on button press in toolInMATLABuserManualPushbutton.
function toolInMATLABuserManualPushbutton_Callback(hObject, eventdata, handles)
% hObject    handle to toolInMATLABuserManualPushbutton (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

userManualURL = 'https://docs.google.com/document/d/1NrMqv29hSLlcY1tQXmT6um9BurBThGxtuJIjONO_HIs/edit?hl=en_US';
    
web(userManualURL, '-browser');

end


function name = getComputerName()
[ret, name] = system('hostname');   

if ret ~= 0,
   if ispc
      name = getenv('COMPUTERNAME');
   else      
      name = getenv('HOSTNAME');      
   end
end
name = lower(name);
end

function name = getUserName ()
    if isunix() 
        name = getenv('USER'); 
    else 
        name = getenv('username'); 
    end
end

% --- Executes on button press in submitFeedbackPushbutton.
function submitFeedbackPushbutton_Callback(hObject, eventdata, handles)
% hObject    handle to submitFeedbackPushbutton (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

    submitFeedback('');
    
end

function submitFeedback(feedbackMessage)
debug('Start of submitFeedback');
global globalHandles;

global globalTimeProgramWasStarted;
global globalCurrentVersionString;
global globalSendSerialPrimitiveAndWaitForBytesReverseLog;

galvanometerIncrement = get(globalHandles.galvanometerIncrementEdit,'String');
galvanometerStartValue = get(globalHandles.galvanometerStartValueEdit,'String');
numberOfLinesPerFrame = get(globalHandles.numberOfLinesPerFrameEdit, 'String');
numberOfLinesForVSync = get(globalHandles.numberOfLinesForVSyncEdit, 'String');
TMR1ReloadValue = get(globalHandles.TMR1ReloadValueEdit, 'String');
iPhotonNumberOfPixelsPerLine = get(globalHandles.iPhotonNumberOfPixelsPerLineEdit, 'String');
polygonSpeedIsFixed = get(globalHandles.polygonSpeedIsFixedCheckbox, 'Value');
fixedPolygonRevolutionsPerMinute = get(globalHandles.fixedPolygonRevolutionsPerMinuteEdit, 'String');

selectedCircuitIndex = get(globalHandles.selectedCircuitPopupmenu,'Value');
selectedCircuitStrings = get(globalHandles.selectedCircuitPopupmenu,'String');
selectedCircuit = selectedCircuitStrings{selectedCircuitIndex};

% TBD must read it directly with primitive. 
% getFirmwareVersionPushbutton_Callback(hObject, eventdata, globalHandles);

selectedCircuitFirmwareVersion = get(globalHandles.firmwareVersionEdit, 'String');
selectedCircuitBuildDateAndTime = get(globalHandles.buildDateAndTimeEdit, 'String');
selectedCircuitCID = get(globalHandles.CIDEdit, 'String');
selectedCircuitCPN = get(globalHandles.CPNEdit, 'String');
selectedCircuitSN = get(globalHandles.SNEdit, 'String');
selectedCircuitSwitches = get(globalHandles.switchesEdit, 'String');

debugLogString = sprintf('timeProgramWasStarted:%s', globalTimeProgramWasStarted);
debugLogString = strcat(debugLogString, '%0D%0A');

serialInterfaceIndex = get(globalHandles.serialInterfacePopupmenu,'Value');
serialInterfaceStrings = get(globalHandles.serialInterfacePopupmenu,'String');
serialInterface = serialInterfaceStrings{serialInterfaceIndex};
debugLogString = strcat(debugLogString, sprintf('videoRateSynchronizationCircuitSerialInterface:%s', serialInterface));
debugLogString = strcat(debugLogString, '%0D%0A');



serialInterfaceIndex = get(globalHandles.polygonSpeedControlCircuitSerialInterfacePopupmenu,'Value');
serialInterfaceStrings = get(globalHandles.polygonSpeedControlCircuitSerialInterfacePopupmenu,'String');
serialInterface = serialInterfaceStrings{serialInterfaceIndex};
debugLogString = strcat(debugLogString, sprintf('polygonSpeedControlCircuitSerialInterface:%s', serialInterface));
debugLogString = strcat(debugLogString, '%0D%0A');

debugLogString = strcat(debugLogString, sprintf('listOfSerialInterfaces:'));
for (i = 1:size(serialInterfaceStrings, 1))
    % Please note the curly braces, not the square brackets to get cell
    % content. Spent too much time on this subtle bug...
    debugLogString = strcat(debugLogString, sprintf(' %s', serialInterfaceStrings{i}));   
end
debugLogString = strcat(debugLogString, '%0D%0A');


debugLogString = strcat(debugLogString, sprintf('galvanometerIncrement:%s', galvanometerIncrement));
debugLogString = strcat(debugLogString, '%0D%0A');
debugLogString = strcat(debugLogString, sprintf('galvanometerStartValue:%s', galvanometerStartValue));
debugLogString = strcat(debugLogString, '%0D%0A');
debugLogString = strcat(debugLogString, sprintf('numberOfLinesPerFrame:%s', numberOfLinesPerFrame));
debugLogString = strcat(debugLogString, '%0D%0A');
debugLogString = strcat(debugLogString, sprintf('numberOfLinesForVSync:%s', numberOfLinesForVSync));
debugLogString = strcat(debugLogString, '%0D%0A');
debugLogString = strcat(debugLogString, sprintf('TMR1ReloadValue:%s', TMR1ReloadValue));
debugLogString = strcat(debugLogString, '%0D%0A');
debugLogString = strcat(debugLogString, sprintf('iPhotonNumberOfPixelsPerLine:%s', iPhotonNumberOfPixelsPerLine));
debugLogString = strcat(debugLogString, '%0D%0A');
debugLogString = strcat(debugLogString, sprintf('polygonSpeedIsFixed:%d', polygonSpeedIsFixed));
debugLogString = strcat(debugLogString, '%0D%0A');
debugLogString = strcat(debugLogString, sprintf('fixedPolygonRevolutionsPerMinute:%s', fixedPolygonRevolutionsPerMinute));
debugLogString = strcat(debugLogString, '%0D%0A');


debugLogString = strcat(debugLogString, sprintf('selectedCircuit:%s', selectedCircuit));
debugLogString = strcat(debugLogString, '%0D%0A');
debugLogString = strcat(debugLogString, sprintf('selectedCircuitFirmwareVersion:%s', selectedCircuitFirmwareVersion));
debugLogString = strcat(debugLogString, '%0D%0A');
debugLogString = strcat(debugLogString, sprintf('selectedCircuitBuildDateAndTime:%s', selectedCircuitBuildDateAndTime));
debugLogString = strcat(debugLogString, '%0D%0A');
debugLogString = strcat(debugLogString, sprintf('selectedCircuitCID:%s', selectedCircuitCID));
debugLogString = strcat(debugLogString, '%0D%0A');
debugLogString = strcat(debugLogString, sprintf('selectedCircuitCPN:%s', selectedCircuitCPN));
debugLogString = strcat(debugLogString, '%0D%0A');
debugLogString = strcat(debugLogString, sprintf('selectedCircuitSN:%s', selectedCircuitSN));
debugLogString = strcat(debugLogString, '%0D%0A');
debugLogString = strcat(debugLogString, sprintf('selectedCircuitSwitches:%s', selectedCircuitSwitches));
debugLogString = strcat(debugLogString, '%0D%0A');

debugLogString = strcat(debugLogString, sprintf('computerName:%s%\n', getComputerName()));
debugLogString = strcat(debugLogString, '%0D%0A');
debugLogString = strcat(debugLogString, sprintf('computerOS:%s', computer()));
debugLogString = strcat(debugLogString, '%0D%0A');
debugLogString = strcat(debugLogString, sprintf('userName:%s', getUserName()));
debugLogString = strcat(debugLogString, '%0D%0A');

debugLogString = strcat(debugLogString, sprintf('versionOfMATLAB:%s', version()));
debugLogString = strcat(debugLogString, '%0D%0A');

debugLogString = strrep(debugLogString, ' ', '%20');

feedbackFormURL = sprintf('https://docs.google.com/spreadsheet/viewform?formkey=dENMYTFFQ1pGakhwRXU4MFZUTlRTcVE6MQ&entry_0=%s&entry_1=%s&entry_3=%s', feedbackMessage, globalCurrentVersionString, debugLogString);

serialDebugLogString = sprintf('globalSendSerialPrimitiveAndWaitForBytesReverseLog:%s', globalSendSerialPrimitiveAndWaitForBytesReverseLog);
serialDebugLogString = strcat(serialDebugLogString, '%0D%0A');

serialDebugLogString = strrep(serialDebugLogString, ' ', '%20');

feedbackFormURL = strcat(feedbackFormURL, serialDebugLogString);

% Having a URL longer than 2000 characters will lead to some
% incompatibilities in some browsers.

lengthOfFeedbackFormURL = length(feedbackFormURL);

if (lengthOfFeedbackFormURL > 2000)
    disp(sprintf('Warning: feedback URL at %d characters is longer than 2000 and will be truncated for compatibility with all browsers.', lengthOfFeedbackFormURL));
    % Must truncate URL.
    feedbackFormURL = feedbackFormURL(1:2000-3);
    feedbackFormURL = strcat(feedbackFormURL, '...'); % Give a hint that URL was truncated.
end

% Note that the internal web browser does not like the feedback form URL in
% some cases. Both Chrome and IE seem so far to cope with it.
web(feedbackFormURL, '-browser');

debug('End of submitFeedback.');
end 


% --- Executes on button press in versboseDebugCheckbox.
function versboseDebugCheckbox_Callback(hObject, eventdata, handles)
% hObject    handle to versboseDebugCheckbox (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

% Hint: get(hObject,'Value') returns toggle state of versboseDebugCheckbox

global globalVerboseDebug;

if (get(hObject,'Value'))
    globalVerboseDebug = 1;
else
    globalVerboseDebug = 0;
end

end

function setGUIElementsBasedOnPolygonSpeedFixedOrNot(polygonSpeedIsFixed, handles)

if (polygonSpeedIsFixed)
    set(handles.polygonSpeedControlCircuitSerialInterfacePopupmenu,'Enable', 'off');
    set(handles.TMR1ReloadValueEdit,'Enable', 'off');
    set(handles.readTMR1ReloadValuePushbutton,'Enable', 'off');
    set(handles.TMR1PresetsPopupmenu,'Enable', 'off');
    set(handles.fixedPolygonRevolutionsPerMinuteEdit,'Enable', 'on');    
    % Make sure we select the only relevant circuit
    set(handles.selectedCircuitPopupmenu,'Value', 1);    
else                  
    % Polygon speed is not fixed
    set(handles.polygonSpeedControlCircuitSerialInterfacePopupmenu,'Enable', 'on');
    set(handles.TMR1ReloadValueEdit,'Enable', 'on');
    set(handles.readTMR1ReloadValuePushbutton,'Enable', 'on');
    set(handles.TMR1PresetsPopupmenu,'Enable', 'on');    
    set(handles.fixedPolygonRevolutionsPerMinuteEdit,'Enable', 'off');       
    set(handles.selectedCircuitPopupmenu,'Enable', 'on');
end

end

% --- Executes on button press in polygonSpeedIsFixedCheckbox.
function polygonSpeedIsFixedCheckbox_Callback(hObject, eventdata, handles)
% hObject    handle to polygonSpeedIsFixedCheckbox (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

% Hint: get(hObject,'Value') returns toggle state of polygonSpeedIsFixedCheckbox

polygonSpeedIsFixed = get(hObject,'Value');
setGUIElementsBasedOnPolygonSpeedFixedOrNot(polygonSpeedIsFixed, handles);
if polygonSpeedIsFixed
    fixedPolygonRevolutionsPerMinuteString = get(handles.fixedPolygonRevolutionsPerMinuteEdit, 'String');   
    if (isempty(fixedPolygonRevolutionsPerMinuteString))
        answer = inputdlg('Enter the fixed polygon speed in revolutions per minute so that rates can be computed. A typical value is 28800 RPM which leads to a typical frame rate of 30 Hz', 'Fixed polygon speed', 1, {'28800'});
        if (isempty(answer))
            return;
        else
            set(handles.fixedPolygonRevolutionsPerMinuteEdit, 'String', answer{1});
        end
    end
end

%computeRatesDeprecated(hObject, eventdata, handles);

end



function fixedPolygonRevolutionsPerMinuteEdit_Callback(hObject, eventdata, handles)
% hObject    handle to fixedPolygonRevolutionsPerMinuteEdit (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of fixedPolygonRevolutionsPerMinuteEdit as text
%        str2double(get(hObject,'String')) returns contents of fixedPolygonRevolutionsPerMinuteEdit as a double

%computeRatesDeprecated(hObject, eventdata, handles);

end

% --- Executes during object creation, after setting all properties.
function fixedPolygonRevolutionsPerMinuteEdit_CreateFcn(hObject, eventdata, handles)
% hObject    handle to fixedPolygonRevolutionsPerMinuteEdit (see GCBO)
% eventdata  reserved
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end

end

function showCommunicationErrorCheckList()
uiwait(errordlg(sprintf(['Make sure of the following:\n\n' ...
    '1) Circuit is turned on\n\n' ...
    '2) The state of the RUN/PROG switch on the circuit is RUN.\n\n' ...
    '3) The circuit is connected to the computer with a plain DB-9 cable, i.e. no missing lines, no line inversions.\n\n' ...
    '4) The serial interface is not locked in a bad state. In this case, restarting MATLAB, logging off or even rebooting the computer may be necessary.\n\n' ...
    '5) You selected the right serial interface to communicate with the circuit.\n\n' ...
    '6) You updated the circuit with the right firmware.\n\n' ...    
    '7) The firmware of the circuit is the latest available. Very old firmware versions may be incompatible with the current version of this tool.\n\n' ...    
    ])));
end

% --- Executes on button press in interactiveConfigurationPushbutton.
function [userCancelled] = interactiveConfigurationPushbutton_Callback(hObject, eventdata, handles)
% hObject    handle to interactiveConfigurationPushbutton (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

userCancelled = 0; % default

interactiveConfigurationQuestion = sprintf(['This will take you through a step by step configuration process of this program and connected circuit(s). Circuits can be emulated so you can use this as a tutorial.\n\n' ...
    'You may decide to exit this process at any time by clicking cancel in the following dialogs.\n\n' ...
    'Do you want to continue?']);
interactiveConfigurationAnswer = questdlg(interactiveConfigurationQuestion, mfilename, 'Yes', 'No', 'Yes');
if not(strcmp(interactiveConfigurationAnswer, 'Yes'))
    userCancelled = 1;
    return;
end

serialInterfaceIndex = get(handles.serialInterfacePopupmenu,'Value');
serialInterfaceStrings = get(handles.serialInterfacePopupmenu,'String');
serialInterface = serialInterfaceStrings{serialInterfaceIndex};

%serialInterfaceString = get(handles.serialInterfacePopupmenu,'String');
%set(handles.serialInterfacePopupmenu,'Value', length(ports));

%sizeOfSerialInterfaceStrings = size(serialInterfaceStrings);

%serialInterfaceInitialValue = sizeOfSerialInterfaceStrings(1); % Emulate by default.

[serialInterface, ok] = listdlg('ListString',serialInterfaceStrings, ...
    'SelectionMode', 'single', ...
    'Name', mfilename, ...
    'PromptString', 'Select the serial interface connected to the video rate synchronization circuit', ...
    'ListSize', [400 100], ...
    'InitialValue', serialInterfaceIndex);

if (ok == 0)
    userCancelled = 1;
    return;
else
    set(handles.serialInterfacePopupmenu, 'Value', serialInterface);    
end

serialInterfaceIndex = get(handles.serialInterfacePopupmenu,'Value');

testCommunicationQuestion = 'Do you want to test communication with the circuit?';

if (serialInterfaceIndex == length(serialInterfaceStrings))
    testCommunicationQuestion = sprintf('%s\n\nNote that since your are in emulation mode this test is trivial.', testCommunicationQuestion);
else
    testCommunicationQuestion = sprintf('%s\n\nMake sure the video rate synchronization circuit is on and connected with a serial cable to this computer.', testCommunicationQuestion);
end

testCommunicationAnswer = questdlg(testCommunicationQuestion, mfilename, 'Yes');
drawnow;

if strcmp(testCommunicationAnswer, 'Yes')
    forcedSelectedCircuitIndex = 1;
    error = getCPNPushbutton_Callback(hObject, eventdata, handles, forcedSelectedCircuitIndex);
    if (error)
        showCommunicationErrorCheckList();
        return;
    else
        msgboxModal('Communication with the circuit is working.');        
    end
    
elseif strcmp(testCommunicationAnswer, 'No')
    
else    
    userCancelled = 1;
    return;
end

polygonSpeedIsFixedQuestion = sprintf(['One option is that this system is running with a fixed-speed polygon, i.e. speed is decided by jumpers on the polygon controller board. See manufacturer user manual for more information.\n\n' ...
    'The other option is to have a circuit controlling the polygon speed to change it dynamically through a TTL clock signal, namely a CPN607 RS-232 programmable TTL frequency generator.\n\n'...
    'Is this system running with a fixed-speed polygon?\n']);

polygonSpeedIsFixedAnswer = questdlg(polygonSpeedIsFixedQuestion, mfilename, 'Yes', 'No', 'Yes');

if strcmp(polygonSpeedIsFixedAnswer, 'Yes')
    polygonSpeedIsFixed = 1;           
    
    fixedPolygonRevolutionsPerMinuteString = get(handles.fixedPolygonRevolutionsPerMinuteEdit, 'String');
    
    if isempty(fixedPolygonRevolutionsPerMinuteString)
        fixedPolygonRevolutionsPerMinuteString = '28800';
    end
    
    prompt={sprintf(['Provide the fixed speed of the polygon. This is specific to each controller.\n\n' ...
        'A typical value is 28800 to get about 30 fps at 576 total lines per frame.\n\n' ...
        'You can ask the technical support of the polygon manufacturer to get the jumper configuration table for your specific serial number.\n'])};
    numlines=1;
    defaultanswer={fixedPolygonRevolutionsPerMinuteString};
    
    answer=inputdlg(prompt, mfilename, numlines, defaultanswer);
    if isempty(answer)
        userCancelled = 1;
        return;
    end
    
    fixedPolygonRevolutionsPerMinuteString = char(answer);    
    set(handles.fixedPolygonRevolutionsPerMinuteEdit, 'String', fixedPolygonRevolutionsPerMinuteString);    
    fixedPolygonRevolutionsPerMinute = str2num(fixedPolygonRevolutionsPerMinuteString);
    polygonRevolutionsPerMinute = fixedPolygonRevolutionsPerMinute;        
    
elseif strcmp(polygonSpeedIsFixedAnswer, 'No')
    
    polygonSpeedIsFixed = 0;
    
    serialInterfaceIndex = get(handles.polygonSpeedControlCircuitSerialInterfacePopupmenu,'Value');
    serialInterfaceStrings = get(handles.polygonSpeedControlCircuitSerialInterfacePopupmenu,'String');
    serialInterface = serialInterfaceStrings{serialInterfaceIndex};
    
    [serialInterface, ok] = listdlg('ListString',serialInterfaceStrings, ...
        'SelectionMode', 'single', ...
        'Name', mfilename, ...
        'PromptString', 'Select serial interface of the polygon speed control circuit', ...
        'ListSize', [400 100], ...
        'InitialValue', serialInterfaceIndex);
    
    if (ok == 0)
        userCancelled = 1;
        return;
    else
        set(handles.polygonSpeedControlCircuitSerialInterfacePopupmenu, 'Value', serialInterface);
    end
    
    
    testCommunicationQuestion = 'Do you want to test communication with the circuit?';
    
    if (serialInterfaceIndex == length(serialInterfaceStrings))
        testCommunicationQuestion = sprintf('%s\n\nNote that since your are in emulation mode this test is trivial.', testCommunicationQuestion);
    else
        testCommunicationQuestion = sprintf('%s\n\nMake sure the polygon speed control circuit is on and connected with a serial cable to this computer.', testCommunicationQuestion);        
    end
    
    testCommunicationAnswer = questdlg(testCommunicationQuestion, mfilename, 'Yes');
    drawnow;
           
    if strcmp(testCommunicationAnswer, 'Yes')
        forcedSelectedCircuitIndex = 2;
        error = getCPNPushbutton_Callback(hObject, eventdata, handles, forcedSelectedCircuitIndex);
        if (error)
            showCommunicationErrorCheckList();
            return;
        else
            msgboxModal('Communication with the circuit is working.');        
        end
        
    elseif strcmp(testCommunicationAnswer, 'No')
        
    else
        userCancelled = 1;
        return;
    end              
    
    TMR1ReloadValueString = get(handles.TMR1ReloadValueEdit, 'String');
    
    if isempty(TMR1ReloadValueString)
        TMR1ReloadValueString = '60327';
    end
    
    prompt={sprintf(['Provide the TMR1 reload value.\n\n' ...
        'It controls the speed of the polygon: the higher this value, the faster it rotates.\n\n' ...
        'The valid range is from 40535 to 60327.\n\n'...
        'Values usually used are 60327 (full speed) and 55119 (50 %% of full speed).\n'])};
    numlines=1;
    defaultanswer={TMR1ReloadValueString};
    
    answer=inputdlg(prompt, mfilename, numlines, defaultanswer);
    if isempty(answer)
        userCancelled = 1;
        return;
    end
    
    TMR1ReloadValueString = char(answer);    
    set(handles.TMR1ReloadValueEdit, 'String', TMR1ReloadValueString);    
    TMR1ReloadValue = str2num(TMR1ReloadValueString);
    
% TBD validation here on TMR1ReloadValue

    polygonClockFrequency = 5000000 / (65535 - TMR1ReloadValue);
    polygonRevolutionsPerMinute = polygonClockFrequency / 2 * 60;
        
else
    userCancelled = 1;
    return;
end

set(handles.polygonSpeedIsFixedCheckbox,'Value', polygonSpeedIsFixed);

setGUIElementsBasedOnPolygonSpeedFixedOrNot(polygonSpeedIsFixed, handles);
drawnow;

if strcmp(polygonSpeedIsFixed, 'No')   
    
    
    
end

galvanometerIncrementString = get(handles.galvanometerIncrementEdit, 'String');
if isempty(galvanometerIncrementString)
    galvanometerIncrementString = '32';
end
prompt={sprintf(['Provide the galvanometer increment.\n\n' ...
    'This controls the level of zoom in Y. The valid range is 0 (linescan) to 65535.\n\n' ...
    'A typical value used for the default zoom level of 1X is 32.\n'])};
numlines=1;
defaultanswer={galvanometerIncrementString};

answer=inputdlg(prompt, mfilename, numlines, defaultanswer);
if isempty(answer)
    userCancelled = 1;
    return;
end

galvanometerIncrementString = char(answer);
set(handles.galvanometerIncrementEdit, 'String', galvanometerIncrementString);
galvanometerIncrement = str2num(galvanometerIncrementString);

numberOfLinesString = get(handles.numberOfLinesPerFrameEdit, 'String');

if isempty(numberOfLinesString)
    numberOfLinesString = '576';
end

prompt={sprintf(['Provide the total number of lines scanned by the galvanometer.\n\n' ...
    'The valid range is 36 to 65520 and it must be a multiple of 36 based on the fact that the polygon has 36 faces and we want lines in the image to be always scanned by the same face of the polygon to avoid annoying scrolling artifacts.\n\n' ...
    'Note that this is not the number of line displayed in iPhoton. Some lines are used for the flyback of the galvanometer.\n\n'...
    'A typical value is 576.\n'])};
numlines=1;
validNumberOfLines = 0;

while (validNumberOfLines == 0)
    defaultanswer={numberOfLinesString};
    answer = inputdlg(prompt, mfilename, numlines, defaultanswer);
    if isempty(answer)
        userCancelled = 1;
        return;       
    end
    numberOfLinesString = char(answer{1});
    if (isempty(numberOfLinesString))
        numberOfLinesString = '576';
        continue;
    end
    
    numberOfLines = str2num(numberOfLinesString);
    if (numberOfLines >= 36 && numberOfLines <= 65520)
        numberOfLinesModulo36 = mod(numberOfLines, 36);
        if (numberOfLinesModulo36 == 0)            
            validNumberOfLines = 1;
            set(handles.numberOfLinesPerFrameEdit, 'String', numberOfLinesString);
        else
            lowerMultipleOf36 = numberOfLines - numberOfLinesModulo36;
            higherMultipleOf36 = lowerMultipleOf36 + 36
            msgboxModal(sprintf('This is not a multiple of 36. The closest numbers meeting this requirement are %d and %d', lowerMultipleOf36, higherMultipleOf36));
            numberOfLinesString = sprintf('%d', higherMultipleOf36);
        end
    else
        msgboxModal('Invalid total number of lines scanned by the galvanometer');
        numberOfLinesString = '576';
    end
end

properGalvanometerStartValue = 32768 - numberOfLines / 2 * galvanometerIncrement;

galvanometerStartValueString = get(handles.galvanometerStartValueEdit, 'String');
if strcmp(galvanometerStartValueString, '')        
    galvanometerStartValueString = sprintf('%d', properGalvanometerStartValue);    
end
prompt={sprintf(['Provide the galvanometer start value. This is for panning in Y.\n\n'...
    'The valid range is 0 to 65535.\n\n' ...
    'Normally, you want the galvanometer position adjusted in its holder so that you image the middle of the field of view in linescan for a value of 32768 (65536 / 2).' ...
    'If your galvanometer is adjusted like this, the proper start value for the chosen zoom level and number of lines is %d.\n'], properGalvanometerStartValue)};
numlines=1;
defaultanswer={galvanometerStartValueString};

answer=inputdlg(prompt, mfilename, numlines, defaultanswer);
if isempty(answer)
    userCancelled = 1;
    return;
end

galvanometerStartValueString = char(answer);
set(handles.galvanometerStartValueEdit, 'String', galvanometerStartValueString);
galvanometerStartValue = str2num(galvanometerStartValueString);


numberOfLinesForVSyncString = get(handles.numberOfLinesForVSyncEdit, 'String');

maximumNumberOfLinesForVSync = numberOfLines - 1;

if isempty(numberOfLinesForVSyncString)
    numberOfLinesForVSyncString = '6';
end

prompt={sprintf(['Provide the number of lines for VSync.\n\n' ...
    'This setting is used for compatibility with different frame grabbers that may require different VSync timing.\n\n' ...
    'The valid range is 1 to %d (number of lines - 1).\n\n' ...
    'A typical value is 6.\n'], maximumNumberOfLinesForVSync)};
numlines=1;

numberOfLinesForVSyncIsValid = 0;

while (not(numberOfLinesForVSyncIsValid))
    
    defaultanswer={numberOfLinesForVSyncString};

    answer=inputdlg(prompt,mfilename,numlines,defaultanswer);
    if isempty(answer)
        userCancelled = 1;
        return;
    end
    numberOfLinesForVSyncString = char(answer{1});
    if (isempty(numberOfLinesForVSyncString))
        numberOfLinesForVSyncString = '6';
        continue;
    end

    numberOfLinesForVSync = str2num(numberOfLinesForVSyncString);

    if (numberOfLinesForVSync < 1)
        uiwait(errordlg('Number of lines for VSync is too low.', mfilename, 'modal'));
        numberOfLinesForVSyncString = '6';
        continue;
    elseif (numberOfLinesForVSync > maximumNumberOfLinesForVSync)
        uiwait(errordlg('Number of lines for VSync is too high.', mfilename, 'modal'));
        numberOfLinesForVSyncString = '6';
        continue;
    end
    
    numberOfLinesForVSyncIsValid = 1;
    
end

set(handles.numberOfLinesForVSyncEdit, 'String', numberOfLinesForVSyncString);

iPhotonNumberOfPixelsPerLineString = get(handles.iPhotonNumberOfPixelsPerLineEdit, 'String');

minimumiPhotonNumberOfPixelsSupported = 1;
maximumiPhotonNumberOfPixelsSupported = 262144;

iPhotonNumberOfPixelsPerLineIsValid = 0;

maximumiPhotonNumberOfPixelsForValidClock = uint32( 20e6 / (polygonRevolutionsPerMinute / 60 * 36));

while (not(iPhotonNumberOfPixelsPerLineIsValid))    
    if strcmp(iPhotonNumberOfPixelsPerLineString, '')
        prompt = {sprintf(['Provide the total pixels per line as set in iPhoton so that a sanity check on the pixel frequency can be computed, which must not be greater than 20 MHz. In iPhotonRT, go to Menu Tools -> Show Acquisition Settings -> Total pixels per line.\n\n' ...
        'Note that the Snapper-PCI-24 card supports a range of %d to %d pixels per line but the version of iPhoton used may not support such a wide range. ' ...
        'iPhotonRT 1.1 beta14 has an upper limit of 2048 pixels and a variable lower limit depending on other iPhoton settings.\n\n' ...
        'Based on your previous choices, the maximum number of pixels per line in iPhoton to respect the 20 MHz limit on the pixel clock would be %d\n\n'], minimumiPhotonNumberOfPixelsSupported, maximumiPhotonNumberOfPixelsSupported, maximumiPhotonNumberOfPixelsForValidClock)};

        numlines=1;
        defaultanswer = {iPhotonNumberOfPixelsPerLineString};

        answer = inputdlg(prompt, mfilename, numlines, defaultanswer);

        if (isempty(answer))
           % User hit cancel.
           return;
        end

        iPhotonNumberOfPixelsPerLineString = char(answer{1});
    end
    if (isempty(iPhotonNumberOfPixelsPerLineString))
        iPhotonNumberOfPixelsPerLineString = '';
        continue;
    end
    
    iPhotonNumberOfPixelsPerLine = str2num(iPhotonNumberOfPixelsPerLineString);
    
    [pixelFrequency HSyncFrequency] = computeRates(iPhotonNumberOfPixelsPerLine, polygonRevolutionsPerMinute);

    frameRate = HSyncFrequency / numberOfLines;
            
    if ((iPhotonNumberOfPixelsPerLine < minimumiPhotonNumberOfPixelsSupported) ...
        || (iPhotonNumberOfPixelsPerLine > maximumiPhotonNumberOfPixelsSupported))
        msgboxModal(sprintf('Error: iPhoton number of pixels per line is outside the valid range of %d to %d.', minimumiPhotonNumberOfPixelsSupported, maximumiPhotonNumberOfPixelsSupported));   
        iPhotonNumberOfPixelsPerLineString = '';
        continue;
    end
    if (iPhotonNumberOfPixelsPerLine > maximumiPhotonNumberOfPixelsForValidClock)
        msgboxModal(sprintf('Error: iPhoton number of pixels per line chosen leads to a pixel clock of %.2f MHz, which is beyond the maximum of 20 MHz.', pixelFrequency / 1e6));   
        iPhotonNumberOfPixelsPerLineString = '';
        continue;        
    end
    iPhotonNumberOfPixelsPerLineIsValid = 1;
end

set(handles.iPhotonNumberOfPixelsPerLineEdit, 'String', iPhotonNumberOfPixelsPerLineString);

msgboxModal(sprintf(['The various choices made lead to the following rates:\n\n' ...
    'Pixel frequency %.2f MHz\n' ...
    'HSync frequency %d kHz\n' ...
    'Polygon revolutions per minute %d rpm\n' ...
    'Frame rate %.1f fps'], pixelFrequency / 1e6, HSyncFrequency, polygonRevolutionsPerMinute, frameRate));   
        
writeSettingsToCircuitsQuestion = sprintf(['Only the graphical user interface was set so far with the settings provided. ' ...
    'To write these settings to the circuits, you would have to click on the button "Write Settings to Circuit(s)".\n\n' ...
    'Note that if you later on change a specific setting, the new value is written to the related circuit when you hit enter.\n\n' ...
    'Do you want to write settings to circuit(s) now?\n']);

writeSettingsToCircuitsAnswer = questdlg(writeSettingsToCircuitsQuestion, mfilename, 'Yes');
drawnow;

if strcmp(writeSettingsToCircuitsAnswer, 'Yes')
    writeSettingsToCircuitPushbutton_Callback(hObject, eventdata, handles);    
elseif strcmp(writeSettingsToCircuitsAnswer, 'No')

else
    userCancelled = 1;
    return;
end

writeSettingsToFileQuestion = sprintf(['Once validated, you may want to save these settings into a file with the button "Write Settings to File".\n\n' ...
    'Do you want to write settings into a file now?\n']);

writeSettingsToFileAnswer = questdlg(writeSettingsToFileQuestion, mfilename, 'Yes');
drawnow;

if strcmp(writeSettingsToFileAnswer, 'Yes')
    writeSettingsToFilePushbutton_Callback(hObject, eventdata, handles);
elseif strcmp(writeSettingsToFileAnswer, 'No')

else
    userCancelled = 1;
    return;
end

% TBD must get current selection of switches on both system.
writeSettingsToBankQuestion = sprintf(['Once validated, you may also want to save these settings into one of 4 non-volatile banks of settings in the connected circuit(s)".\n\n' ...
        'When a circuit is powered up. It checks the current selection of the bank switches, see if the corresponding non-volatile memory contains valid settings and use them in this case.\n\n' ...
        'If the bank contains no valid settings, some default settings will be used but that may not be appropriate for your specific system.\n' ...
        'That`s why it is a good idea to program the bank selected on power-up with valid and actually the most often used settings on your system.\n\n' ... 
    'Do you want to write the current settings used by the circuit(s) into the the selected bank of each circuit now?\n\n']);

if strcmp(writeSettingsToCircuitsAnswer, 'No')
   writeSettingsToBankQuestion = sprintf(['%sWarning: since you chose not to write the settings selected in the previous dialogs to the circuit(s), you may end up with unexpected results.' ...
       'You should skip this step then write the settings to the circuit(s) and validate these in actual imaging conditions. Once validated you should write them sequentially in the selected bank of each of the circuits using the "Save Settings to Bank of Selected Circuit"\n\n'], writeSettingsToBankQuestion); 
end

writeSettingsToBankAnswer = questdlg(writeSettingsToBankQuestion, mfilename, 'Yes');
drawnow;

if strcmp(writeSettingsToBankAnswer, 'Yes')        
    set(handles.statusEdit,'String','Getting state of switches of video rate synchronization circuit...');
    drawnow;

    expectedNumberOfBytes = 1;
    
    forcedSelectedCircuitIndex = 1;
    bytesReturned = sendSerialPrimitiveAndWaitForBytes(handles, READ_STATE_OF_SWITCHES_AND_TTL_IOS, expectedNumberOfBytes, forcedSelectedCircuitIndex);
    if (numel(bytesReturned) < expectedNumberOfBytes)
        errorDialogAndStatus(sprintf('Error: could not get the expected number of bytes (%d) while reading state of switches of video rate synchronization circuit.', expectedNumberOfBytes), mfilename, handles);        
        return;
    else
        stateOfSwitchesVideoRateSynchronizationCircuit = bitand(bytesReturned(1),3);
        debug(sprintf('The current state of the switches of the video rate synchronization circuit is: %d\n', stateOfSwitchesVideoRateSynchronizationCircuit));
        set(handles.statusEdit,'String','');
        drawnow;
    end
    
    
    if (not(polygonSpeedIsFixed))    
        set(handles.statusEdit,'String','Getting state of switches of polygon speed control circuit...');
        drawnow;
        
        forcedSelectedCircuitIndex = 2;
        bytesReturned = sendSerialPrimitiveAndWaitForBytes(handles, READ_STATE_OF_SWITCHES_AND_TTL_IOS, expectedNumberOfBytes, forcedSelectedCircuitIndex);
        if (numel(bytesReturned) < expectedNumberOfBytes)
            errorDialogAndStatus(sprintf('Error: could not get the expected number of bytes (%d) while reading state of switches of polygon speed control circuit.', expectedNumberOfBytes), mfilename, handles);        
            return;
        else
            stateOfSwitchesPolygonSpeedControlCircuit = bitand(bytesReturned(1),3);
            debug(sprintf('The current state of the switches of the polygon speed control circuit is: %d\n', stateOfSwitchesPolygonSpeedControlCircuit));
            set(handles.statusEdit,'String','');
            drawnow;
        end               
        forcedSelectedCircuitIndex = 2;
        command = [WRITE_SETTINGS_TO_PRESET_BANK stateOfSwitchesPolygonSpeedControlCircuit];
        numberOfExpectedBytes = 0;
        bytesReturned = sendSerialPrimitiveAndWaitForBytes(handles, command, numberOfExpectedBytes, forcedSelectedCircuitIndex);
        if (bytesReturned == -1)
            msgboxModal(sprintf('Error: Could not write settings to bank %d of polygon speed control circuit.', stateOfSwitchesPolygonSpeedControlCircuit));    
            return;
        else
            msgboxModal(sprintf('The current settings were written into bank %d of the polygon speed control circuit.', stateOfSwitchesPolygonSpeedControlCircuit));    
        end

    end
    
    forcedSelectedCircuitIndex = 1;
    command = [WRITE_SETTINGS_TO_PRESET_BANK stateOfSwitchesVideoRateSynchronizationCircuit];
    numberOfExpectedBytes = 0;
    bytesReturned = sendSerialPrimitiveAndWaitForBytes(handles, command, numberOfExpectedBytes, forcedSelectedCircuitIndex);
    if (bytesReturned == -1)
        msgboxModal(sprintf('Error: Could not write settings to bank %d of video rate synchronization circuit.', stateOfSwitchesVideoRateSynchronizationCircuit));
        return;
    else
        msgboxModal(sprintf('The current settings were written into bank %d of the video rate synchronization circuit.', stateOfSwitchesVideoRateSynchronizationCircuit));    
    end    
    
elseif strcmp(writeSettingsToBankAnswer, 'No')
        msgBox('You may want to write settings currently used by a circuit later on by using the "Save Settings to Bank of Selected Circuit" button.'); 
else
    userCancelled = 1;
    return;
end


end


% --- Executes on button press in checkForNewVersionPushbutton.
function checkForNewVersionPushbutton_Callback(hObject, eventdata, handles)
% hObject    handle to checkForNewVersionPushbutton (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

[versionComparison, latestVersion] = checkForNewVersion();

end

% A bunch of functions that behave like constants.

function [byteCode] = READ_CPN
byteCode = hex2dec('6D');
end

function [byteCode] = READ_FIRMWARE_VERSION
byteCode = hex2dec('7F');
end

function [byteCode] = READ_CID
byteCode = hex2dec('6C');
end

function [byteCode] = READ_SN
byteCode = hex2dec('6B');
end

function [byteCode] = READ_EEPROM_ADDRESS
byteCode = hex2dec('76');
end

function [byteCode] = SWITCH_TO_BOOTLOADER_MODE
byteCode = hex2dec('79');
end

function [byteCode] = READ_STATE_OF_SWITCHES_AND_TTL_IOS
byteCode = hex2dec('7E');
end

function [byteCode] = WRITE_SETTINGS_TO_PRESET_BANK
byteCode = hex2dec('78');
end

function [byteCode] = LOAD_SETTINGS_FROM_PRESET_BANK
byteCode = hex2dec('77');
end

function [byteCode] = READ_BUILD_TIME
byteCode = hex2dec('6A');
end

function [byteCode] = READ_BUILD_DATE
byteCode = hex2dec('69');
end

% CPN607 is for RS-232 programmable TTL frequency generator

function [byteCode] = DISABLE_POLYGON_CLOCK
byteCode = hex2dec('71');
end

function [byteCode] = ENABLE_POLYGON_CLOCK
byteCode = hex2dec('70');
end

function [byteCode] = WRITE_TMR1_RELOAD
byteCode = hex2dec('7D');
end

function [byteCode] = READ_TMR1_RELOAD
byteCode = hex2dec('75');
end

% CPN522 is for Blanker six-channel multiplexer and video rate
% synchronization circuit

function [byteCode] = WRITE_NUMBER_OF_LINES_PER_FRAME
byteCode = hex2dec('7C');
end

function [byteCode] = WRITE_DAC_START
byteCode = hex2dec('7B');
end

function [byteCode] = WRITE_DAC_INCREMENT
byteCode = hex2dec('7A');
end

function [byteCode] = READ_NUMBER_OF_LINES_PER_FRAME
byteCode = hex2dec('74');
end

function [byteCode] = READ_DAC_START
byteCode = hex2dec('73');
end

function [byteCode] = READ_DAC_INCREMENT
byteCode = hex2dec('72');
end

function [byteCode] = READ_NUMBER_OF_LINES_FOR_VSYNC
byteCode = hex2dec('6E');
end

function [byteCode] = WRITE_NUMBER_OF_LINES_FOR_VSYNC
byteCode = hex2dec('6F');
end


% --- Executes on button press in checkForNewVersionOfFirmwarePushbutton.
function checkForNewVersionOfFirmwarePushbutton_Callback(hObject, eventdata, handles)
% hObject    handle to checkForNewVersionOfFirmwarePushbutton (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

selectedCircuitPopupmenu = handles.selectedCircuitPopupmenu;
selectedCircuitIndex = get(selectedCircuitPopupmenu,'Value');
selectedCircuitStrings = get(selectedCircuitPopupmenu,'String');
selectedCircuit = selectedCircuitStrings{selectedCircuitIndex};

if (selectedCircuitIndex == 2)
    serialInterfacePopupmenu = handles.polygonSpeedControlCircuitSerialInterfacePopupmenu;
else
    serialInterfacePopupmenu = handles.serialInterfacePopupmenu;
end

serialInterfaceIndex = get(serialInterfacePopupmenu,'Value');
serialInterfaceStrings = get(serialInterfacePopupmenu,'String');
serialInterface = serialInterfaceStrings{serialInterfaceIndex};

if (serialInterfaceIndex == length(serialInterfaceStrings)) % Test for last string which is "Emulate"
    % We are in emulation.
    uiwait(warndlg('Note that checking for a new version while being in circuit emulation is irrelevant.'));
end
    

[error firmwareVersion] = getFirmwareVersionPushbutton_Callback(hObject, eventdata, handles);
drawnow;

if (firmwareVersion ~= -1)
    set(handles.statusEdit,'String','Checking for a new firmware version...');
        
    if (selectedCircuitIndex == 2)
        % 
        latestVersionOfMicrocontrollerFirmwareHeaderURL = 'https://docs.google.com/uc?id=0B2oqdvmvAX40NTAwYjgyZmMtYjNjOS00NDcwLTljOTYtYmI2N2FjZTFiZDE4&export=download&hl=en_US';    
                                                          %https://docs.google.com/uc?id=0B2oqdvmvAX40NTAwYjgyZmMtYjNjOS00NDcwLTljOTYtYmI2N2FjZTFiZDE4
        latestVersionOfMicrocontrollerFirmwareURL = 'https://docs.google.com/leaf?id=0B2oqdvmvAX40Mjk4ZTM1NzktYzA1Yy00ODIwLWJjNGUtMGUzOTlhOTIyNjA4&hl=en_US';        
    else
        latestVersionOfMicrocontrollerFirmwareHeaderURL = 'https://docs.google.com/uc?id=0B2oqdvmvAX40MTVkYmM4YzItZjE4Ny00ODRjLWEyNjQtMmM1MzVmM2NjYTk1&export=download&hl=en_US';
                                                          %https://docs.google.com/uc?id=0B2oqdvmvAX40MTVkYmM4YzItZjE4Ny00ODRjLWEyNjQtMmM1MzVmM2NjYTk1
        latestVersionOfMicrocontrollerFirmwareURL = 'https://docs.google.com/leaf?id=0B2oqdvmvAX40ZTg0ZDYzYTItYzBjMS00MGQ0LTlkN2UtMDhiNTUzYzI5MGZh&hl=en_US';
    end    
    
    [latestVersion changeLog errorMessage] = getLatestMicrocontrollerFirmwareVersion(latestVersionOfMicrocontrollerFirmwareHeaderURL);
    if (latestVersion ~= -1)
        newVersionAvailable = compareVersion(firmwareVersion, latestVersion);
        if (newVersionAvailable)
            answer = questdlg(sprintf('There is a newer version of the microcontroller firmware available, i.e. %d.%d.%d\n\nDo you want to see the change log?', latestVersion(1), latestVersion(2), latestVersion(3)), ...
                         'New Version of Microcontroller Firmware Available', ...
                         'Yes', 'No', 'Yes');
                     switch answer,
                         case 'Yes',
                             disp(changeLog);
                             prompt = sprintf('Press enter to continue.\n');
                             answer = input(prompt, 's');                             
                         case 'No',                             
                     end % switch
            
            answer = questdlg('Do you want to launch a web browser to fetch the .hex file and see the online user manual for details on how to update it?', ...
                         'New Version of Microcontroller Firmware Available', ...
                         'Yes', 'No', 'Yes');
                     switch answer,
                         case 'Yes',
                             fetchOnlineUserManual(hObject, eventdata, handles);
                             web(latestVersionOfMicrocontrollerFirmwareURL, '-browser');                                                          
                         case 'No',                             
                     end % switch                                 
        else
            msgboxModal(sprintf('Microcontroller firmware version is up to date, latest version is %d.%d.%d', latestVersion(1), latestVersion(2), latestVersion(3)));            
        end
    else
        disp('Debug: error while trying to get latest microcontroller firmware version');
    end
    
else
    % error already reported.
    % msgboxModal('Error: could not get firmware version.');    
end

set(handles.statusEdit,'String','');

end


% --- Executes on button press in writeSettingsToCircuitsAfterLoadingFromFileCheckbox.
function writeSettingsToCircuitsAfterLoadingFromFileCheckbox_Callback(hObject, eventdata, handles)
% hObject    handle to writeSettingsToCircuitsAfterLoadingFromFileCheckbox (see GCBO)
% eventdata  reserved
% handles    structure with handles and user data (see GUIDATA)

% Hint: get(hObject,'Value') returns toggle state of writeSettingsToCircuitsAfterLoadingFromFileCheckbox


end


% --- Executes on button press in stopPolygonCheckbox.
function stopPolygonCheckbox_Callback(hObject, eventdata, handles)
% hObject    handle to stopPolygonCheckbox (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hint: get(hObject,'Value') returns toggle state of stopPolygonCheckbox

polygonSpeedIsFixed = get(handles.polygonSpeedIsFixedCheckbox,'Value');

if (polygonSpeedIsFixed)
    msgboxModal(sprintf(['These instructions are for Lincoln Laser model DT-26-290-025 polygon controlled by a Lincoln Laser MC-5 controller.\n\n' ...
        'You may want to stop the polygon for alignment of the system, since your polygon has a fixed speed and is not controllable by this tool, you can stop it by ' ...
        'disconnecting pin J1-4 (/Enable) from pin J1-2 (Gnd). See MC-5 user manual for more information.\n\n']));
    set(hObject,'Value',0.0);        
    drawnow;
else
    
    stopPolygon = get(hObject,'Value');
    if (stopPolygon)        
        set(handles.statusEdit,'String', 'Stopping polygon...');
        drawnow

        bytesReturned = sendSerialPrimitiveAndWaitForBytes(handles, DISABLE_POLYGON_CLOCK, 0);

        if (bytesReturned == -1)
            msgboxModal('Error: Could not disable polygon clock for stopping polygon.');    
        end
        
        set(handles.statusEdit,'String','');
        drawnow
    else
        set(handles.statusEdit,'String', 'Starting polygon...');
        drawnow

        bytesReturned = sendSerialPrimitiveAndWaitForBytes(handles, ENABLE_POLYGON_CLOCK, 0);

        if (bytesReturned == -1)
            msgboxModal('Error: Could not enable polygon clock for starting polygon.');    
        end
        
        set(handles.statusEdit,'String','');
        drawnow        
    end
    
end
    
end
