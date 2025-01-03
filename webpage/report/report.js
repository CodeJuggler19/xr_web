const companyName = getCookie("company");

class Inspection {
  constructor(topic, instructionList) {
    this.topic = topic;
    this.instruction_list = instructionList;
  }

  changeTopicName(topic) {
    this.topic = topic;
  }

  // Instruction 객체를 추가하는 함수
  addInstruction(instruction) {
    this.instruction_list.push(instruction);
  }

  setInstruction(instructionList) {}
}

class Instruction {
  constructor(instruction, instructionType, options, answer, imgUrl) {
    this.instruction = instruction;
    this.instruction_type = instructionType;
    // 이미지 넣는 부분 작업할 것
    this.img_url = imgUrl;

    // console.log(options);
    // console.log(answer);

    if (options == null) {
      //console.log("options가 null이에요");
      this.options = [];
    } else {
      this.options = options;
    }

    if (answer == null) {
      this.answer = this.createDefaultAnswer();
    } else {
      this.answer = answer;
    }
  }
  createDefaultAnswer() {
    //console.log(this.instruction_type);
    if (this.instruction_type == "check") return ["true"];
    else if (this.instruction_type == "numeric_input") return ["0"];
    else {
      console.log(this.instruction_type);
      return [this.options[0]];
    }
  }
}

class JsonData {
  constructor(infra, inspectionList) {
    this.company_name = getCookie("company");
    this.infra = infra;
    this.last_modified_time = this.currentUnixTime();
    this.inspection_list = inspectionList;
  }

  currentUnixTime() {
    return Math.floor(Date.now() / 1000).toString();
  }

  toJsonString() {
    return JSON.stringify(this, null, 2);
  }
}

let inspectionList = [];
let jsonString;
let jsonData;
let container;

// 새로운 토픽을 추가하는 함수
function addTopic() {
  const topicElement = document.createElement("div"); // 새로운 토픽 요소 생성
  const topicNameInput = document.createElement("input"); // 토픽 이름 입력 필드 생성
  const addInstructionBtn = document.createElement("button"); // "Add Instruction" 버튼 생성
  const instructionContainer = document.createElement("div"); // 지시사항을 담을 컨테이너 생성
  const toggleInstructionsBtn = document.createElement("button"); // Instruction 토글 버튼 생성

  topicElement.classList.add("topic");
  instructionContainer.classList.add("instructionContainer");

  // 토픽 이름 입력 필드 속성 설정
  topicNameInput.setAttribute("type", "text");
  topicNameInput.setAttribute("placeholder", "토픽 입력");
  topicNameInput.setAttribute("maxlength", "10"); // 10자 제한 속성 추가
  topicNameInput.classList.add("topicInput"); // 클래스 추가

  // "Add Instruction" 버튼 텍스트 설정
  addInstructionBtn.textContent = "질문 추가";
  addInstructionBtn.classList.add("addInstructionBtn"); // 클래스 추가

  // Instruction 토글 버튼 텍스트 및 속성 설정
  toggleInstructionsBtn.textContent = "질문 숨기기/보이기";
  toggleInstructionsBtn.classList.add("toggleInstructionBtn"); // 클래스 추가

  //임시 삭제 버튼
  const deleteBtn = document.createElement("button");
  deleteBtn.textContent = "삭제";
  deleteBtn.classList.add("delete-btn");
  deleteBtn.addEventListener("click", function () {
    // 삭제 버튼 클릭 시 해당 input을 포함한 부모 요소를 삭제합니다.
    topicElement.remove();
  });

  // 생성한 요소들을 토픽 요소에 추가
  topicElement.appendChild(topicNameInput);
  topicElement.appendChild(addInstructionBtn);
  topicElement.appendChild(toggleInstructionsBtn); // 토글 버튼 추가
  topicElement.appendChild(deleteBtn); // 삭제 버튼 추가
  topicElement.appendChild(instructionContainer); // 지시사항 컨테이너를 토픽 요소에 추가
  container.appendChild(topicElement); // 토픽 요소를 컨테이너에 추가

  // "Add Instruction" 버튼 클릭 시 실행될 함수
  addInstructionBtn.addEventListener("click", function () {
    addInstruction(instructionContainer);
  });

  // "Toggle Instructions" 버튼 클릭 시 실행될 함수
  toggleInstructionsBtn.addEventListener("click", function () {
    toggleInstructions(instructionContainer);
  });
}

// 지시사항 숨기기/보이기 토글 함수
function toggleInstructions(instructionContainer) {
  // instructionContainer의 display 속성을 토글하여 숨기거나 보여줌
  if (instructionContainer.style.display === "none") {
    instructionContainer.style.display = "block";
  } else {
    instructionContainer.style.display = "none";
  }
}

// 질문 추가 버튼 눌렀을 때 실행될 부분
function addInstruction(instructionContainer) {
  const instructionElement = document.createElement("div"); // 새로운 지시사항 요소 생성
  const instructionInput = document.createElement("input"); // 지시사항 입력 필드 생성
  const instructionTypeSelect = document.createElement("select"); // instructionType 선택 셀렉트 태그 생성

  //임시 삭제 버튼
  const deleteBtn = document.createElement("button");
  deleteBtn.textContent = "삭제";
  deleteBtn.classList.add("delete-btn");
  deleteBtn.addEventListener("click", function () {
    // 삭제 버튼 클릭 시 해당 input을 포함한 부모 요소를 삭제합니다.
    instructionElement.remove();
  });

  const options = document.createElement("div"); // 옵션 div 생성
  options.classList.add("options");
  const optionsContainer = document.createElement("div"); // 옵션 리스트 컨테이너 생성

  optionsContainer.classList.add("optionsContainer");

  // 옵션에 새 원소를 추가하는 버튼
  const addOptionBtn = document.createElement("button");
  addOptionBtn.textContent = "선택지 추가";
  addOptionBtn.classList.add("addOptionBtn");

  // 옵션 리스트를 숨김/보임 토글하는 버튼
  const toggleOptionsBtn = document.createElement("button");
  toggleOptionsBtn.textContent = "선택지 숨기기/보이기";
  toggleOptionsBtn.classList.add("toggleOptionBtn");

  // "Toggle Instructions" 버튼 클릭 시 실행될 함수
  toggleOptionsBtn.addEventListener("click", function () {
    toggleOptions(instructionContainer);
  });

  optionsContainer.appendChild(addOptionBtn);

  // 이미지 업로드 기능
  const uploadForm = document.createElement("form");
  uploadForm.id = "upload-form";

  // 파일 input
  const fileInput = document.createElement("input");
  // input 요소의 속성 설정
  fileInput.type = "file";
  fileInput.id = "image-file";
  fileInput.name = "file";
  fileInput.accept = "image/*";
  uploadForm.appendChild(fileInput);

  // 업로드 버튼
  const fileSubmitBtn = document.createElement("button");
  fileSubmitBtn.type = "submit";
  fileSubmitBtn.textContent = "이미지 업로드";
  uploadForm.appendChild(fileSubmitBtn);

  // 주소 저장 텍스트
  const imgUrlText = document.createElement("input");
  imgUrlText.type = "hidden";
  imgUrlText.classList.add("img_url");
  uploadForm.appendChild(imgUrlText);

  const sampleImage = document.createElement("img");
  sampleImage.classList.add("example-image");
  uploadForm.appendChild(sampleImage);

  // 업로드 폼의 submit 이벤트에 핸들러 연결
  uploadForm.addEventListener("submit", function (event) {
    handleImageUpload(event, uploadForm);
  });

  instructionElement.appendChild(uploadForm);

  instructionElement.classList.add("instruction");

  // 지시사항 입력 필드 속성 설정
  instructionInput.setAttribute("type", "text");
  instructionInput.setAttribute("placeholder", "Instruction");
  instructionInput.classList.add("instructionInput");
  instructionInput.setAttribute("maxlength", "25"); // 10자 제한 속성 추가

  instructionTypeSelect.classList.add("instructionTypeSelect");

  // instruction Type을 변경했을 때 호출됨
  instructionTypeSelect.addEventListener("change", function (event) {
    const selectedValue = event.target.value; //변경된 값 가져옴

    const parentDiv = event.target.parentElement; // select 요소의 부모 요소 가져오기
    const optionsContainer = parentDiv.querySelector(".optionsContainer"); // options 컨테이너 찾기
    console.log(selectedValue);

    // 선택한 값이 "multipleChoice" 또는 "multipleSelect"인 경우
    if (
      selectedValue === "multiple_choice" ||
      selectedValue === "multiple_select"
    ) {
      console.log("선택지 띄울게요");
      // 숨겨진 div를 보이도록 설정
      optionsContainer.style.display = "block";
    } else {
      // 다른 경우, 숨깁니다.
      console.log("선택지를 숨길게요");
      optionsContainer.style.display = "none";
    }
  });

  // instructionType 선택 셀렉트 태그 옵션 설정
  const optionValues = [
    "check",
    "single_choice",
    "multiple_choice",
    "multiple_select",
    "numeric_input",
  ];
  const optionTexts = [
    "체크",
    "예/아니오 선택",
    "단일 선택",
    "복수 선택",
    "수치 입력",
  ];

  for (let i = 0; i < optionValues.length; i++) {
    const option = document.createElement("option");
    option.value = optionValues[i];
    option.textContent = optionTexts[i];
    instructionTypeSelect.appendChild(option);
  }

  // 생성한 요소들을 지시사항 요소에 추가
  instructionElement.appendChild(instructionInput);
  instructionElement.appendChild(instructionTypeSelect);
  instructionElement.appendChild(deleteBtn);
  instructionContainer.appendChild(instructionElement); // 지시사항을 토픽 요소의 컨테이너에 추가
  instructionElement.appendChild(optionsContainer);

  addOptionBtn.addEventListener("click", function () {
    addOption(optionsContainer);
  });
  optionsContainer.style.display = "none";
}

// 선택지 숨기기/보이기 토글 함수
function toggleOptions(optionContainer) {
  // instructionContainer의 display 속성을 토글하여 숨기거나 보여줌
  if (optionContainer.style.display === "none") {
    optionContainer.style.display = "block";
  } else {
    optionContainer.style.display = "none";
  }
}

function addOption(optionsContainer) {
  optionsLength = optionsContainer.querySelectorAll(".option").length;
  if (optionsLength >= 5) {
    alert("선택지는 최대 5개까지 추가할 수 있습니다!");
    return;
  }

  const optionElement = document.createElement("div");
  optionElement.classList.add("option");

  const optionInput = document.createElement("input");
  optionInput.setAttribute("type", "text");
  optionInput.setAttribute("placeholder", "Option");
  optionInput.setAttribute("maxlength", "5"); // 10자 제한 속성 추가

  const deleteBtn = document.createElement("button");
  deleteBtn.textContent = "Delete";
  deleteBtn.classList.add("delete-btn");
  deleteBtn.addEventListener("click", function () {
    // 삭제 버튼 클릭 시 해당 input을 포함한 부모 요소를 삭제합니다.
    optionElement.remove();
  });

  optionElement.appendChild(optionInput);
  optionElement.appendChild(deleteBtn);

  optionsContainer.appendChild(optionElement);
}

// 옵션들을 가져오는 함수
function getOptions(_instruction, instructionType) {
  console.log(`get Options : ${instructionType}`);
  console.log(_instruction);
  let options = [];

  switch (instructionType) {
    case "check":
      return null;
    case "single_choice":
      options = ["예", "아니오"];
      break;
    case "numeric_input":
      return null;
    case "multiple_choice":
    case "multiple_select":
      const optionContainer = _instruction.querySelector(".optionsContainer");
      console.log(optionContainer);

      const optionList = _instruction.querySelectorAll(
        ".optionsContainer > div"
      );

      console.log(optionList);

      optionList.forEach(function (optionElement) {
        let value = optionElement.querySelector("input[type='text']").value;
        options.push(value);
      });
      break;
  }

  return options;
}

function saveReportForm() {
  if (checkEmptyInputs()) return;
  generateJson();
}

function checkEmptyInputs() {
  const inputs = document.querySelectorAll(
    "input:not([type='file']):not([type='hidden'])"
  ); // 파일 및 숨겨진 input 제외
  let isEmpty = false;

  inputs.forEach(function (input) {
    if (input.value.trim() === "") {
      isEmpty = true;
    }
  });

  if (isEmpty) {
    alert("빈 입력 필드가 있습니다. 모두 채워주세요.");
    return true;
  }
  return false;
}

// JSON을 생성하고 화면에 표시하는 함수
function generateJson() {
  const infraName = document.getElementById("infraSelect").value;

  const topicElements = document.querySelectorAll(".topic"); // topicInput 클래스에 속한 요소들 가져오기

  // 각 토픽 요소를 순회하며 정보를 가져오기
  topicElements.forEach(function (topicElement) {
    const topicName = topicElement.querySelector("input[type='text']").value; // 토픽 이름 가져오기
    const instructionList = []; // 각 토픽의 지시사항 목록을 담을 배열 초기화
    const instructionElements = topicElement.querySelectorAll(".instruction");

    console.log(instructionElements);

    const instructionInputs = topicElement.querySelectorAll(
      "div .instructionInput"
    ); // 각 토픽의 지시사항 입력 요소들 가져오기
    const instructionTypeElements = topicElement.querySelectorAll(
      "div .instructionTypeSelect"
    ); // 각 토픽의 instructionType 선택 요소들 가져오기

    // 각 지시사항 입력 요소와 instructionType 선택 요소를 순회하며 정보를 가져와서 Instruction 객체를 만들고 instructionList에 추가
    for (let i = 0; i < instructionElements.length; i++) {
      let instruction = instructionElements[i];
      let inputValue = instruction.querySelector(".instructionInput");
      const instructionValue = inputValue.value;

      let inputText = instruction.querySelector(".instructionTypeSelect");
      const instructionType = inputText.value;

      //const instructionType = instructionTypeElements[i].value; // 선택한 instructionType 가져오기
      console.log(instructionValue, instructionType);

      // 이미지 주소 없는지 확인해보자
      const formElement = instruction.querySelector("#upload-form"); // 지시사항 내의 upload-form 가져오기
      console.log("form Element 불러오기");
      console.log * formElement;
      const imgUrlInput = formElement.querySelector("input.img_url");
      const imgUrl = imgUrlInput.value;
      console.log(`이미지 주소  ${imgUrlInput.value}`);

      const instructionObject = new Instruction(
        instructionValue,
        instructionType,
        getOptions(instruction, instructionType),
        null,
        imgUrl
      ); // Instruction 객체 생성
      instructionList.push(instructionObject); // instructionList에 추가
    }

    const inspection = new Inspection(topicName, instructionList);
    inspectionList.push(inspection);
  });

  jsonData = new JsonData(infraName, inspectionList);

  //const jsonOutputElement = document.getElementById("jsonOutput");
  jsonString = jsonData.toJsonString();
  //jsonOutputElement.textContent = jsonString; // 들여쓰기 2로 설정하여 가독성 향상
  //console.log(jsonString);
  sendRequest(jsonData);
}

function sendRequest(jsonData) {
  // HTTP POST 요청을 보낼 URL
  const url = "https://" + window.location.hostname + "/api/report";
  jsonString = jsonData.toJsonString();
  console.log(jsonString);

  // HTTP 요청 옵션 설정
  const requestOptions = {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(jsonData),
  };

  // Fetch API를 사용하여 HTTP 요청 보내기
  fetch(url, requestOptions)
    .then((response) => {
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      return response.json();
    })
    .then((data) => {
      console.log("Response:", data);
      alert("절차 생성 완료!");
      // 여기서 응답에 대한 작업을 수행합니다.
    })
    .catch((error) => {
      alert(`절차 생성 실패. 사유:${error}`);
      console.error("There was a problem with the request:", error);
      // 여기서 오류 처리를 수행합니다.
    });
}

function addOptionsToInfraOption(optionsArray) {
  // Get the select element by its ID
  const select = document.getElementById("infraSelect");

  // Clear existing options
  select.innerHTML = "";

  // Iterate over the array and create option elements
  optionsArray.forEach((optionValue) => {
    // Create a new option element
    const option = document.createElement("option");
    option.value = optionValue;
    option.textContent = optionValue; // Set the text content of the option

    // Append the option to the select
    select.appendChild(option);
  });
}

function fetchInfraList() {
  // fetch 함수는 프로미스를 반환하므로 해당 프로미스를 반환
  return fetch(`/api/infras?company_name=${companyName}`)
    .then((response) => response.json())
    .then((data) => {
      // 서버에서 받은 데이터 반환
      return data;
    });
}

// HTML 문서가 로드되면 실행됨
document.addEventListener("DOMContentLoaded", function () {
  console.log(getCookie("company"));
  container = document.getElementById("report-container");
  console.log(container);
  const addTopicBtn = document.getElementById("addTopicBtn");
  const generateJsonBtn = document.getElementById("generateJsonBtn");

  // fetchInfraList 함수를 호출하고 반환된 프로미스를 이용하여 데이터를 처리
  fetchInfraList()
    .then((data) => {
      // 받은 데이터를 infraArray 변수에 할당
      console.log(data.infra_list); // 할당된 데이터 출력
      addOptionsToInfraOption(data.infra_list);
    })
    .catch((error) => {
      console.error("Error fetching infra list:", error);
    });

  // "Add Topic" 버튼 클릭 시 실행될 함수
  addTopicBtn.addEventListener("click", function () {
    addTopic();
  });

  // "Generate Json" 버튼 클릭 시 실행될 함수
  generateJsonBtn.addEventListener("click", function () {
    saveReportForm();
    //generateJson();
  });
});

// 이미지 submit 버튼 클릭시 실행될 함수
// 이미지 업로드 함수
async function handleImageUpload(event, formElement) {
  event.preventDefault(); // 폼 기본 제출 동작 방지

  const fileInput = formElement.querySelector("input[type='file']"); // 해당 폼 내의 파일 input 선택
  const file = fileInput.files[0];
  // 이미지 주소 입력할 곳 가져오기
  const imgUrlInput = formElement.querySelector("input.img_url"); // .img_url 클래스를 가진 hidden input 선택

  if (!file) {
    alert("Please select a file to upload.");
    return;
  }

  // FormData에 파일 추가
  const formData = new FormData();
  formData.append("file", file);

  try {
    // 이미지 업로드 API 호출
    const response = await fetch("https://xrweb.kro.kr/api/upload-image", {
      method: "POST",
      body: formData,
    });

    if (response.ok) {
      const data = await response.json();
      const uploadedImageUrl = data.url; // 업로드된 이미지 URL
      imgUrlInput.value = uploadedImageUrl;

      // img 요소를 가져와서 src에 URL을 등록
      const imgElement = formElement.querySelector("img.example-image");
      if (imgElement) {
        imgElement.src = uploadedImageUrl; // 업로드된 이미지 URL로 설정
      } else {
        console.error("Image element not found.");
      }

      alert("Image uploaded successfully!");
    } else {
      const errorData = await response.json();
      alert(`Error: ${errorData.error}`);
    }
  } catch (error) {
    console.error("Error uploading the image:", error);
    alert("Error uploading the image. Please try again later.");
  }
}
