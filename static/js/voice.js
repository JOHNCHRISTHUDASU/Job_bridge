// =================================
// JobBridge Job Seeker Voice Feature
// =================================

console.log("Voice JS Loaded");


// ===============================
// 🎤 Voice Search
// ===============================

const voiceSearchBtn = document.getElementById("voiceSearch");


if (voiceSearchBtn) {


    voiceSearchBtn.addEventListener("click", function(){


        const SpeechRecognition =
        window.SpeechRecognition ||
        window.webkitSpeechRecognition;



        if(!SpeechRecognition){

            alert(
            "Voice search is not supported. Use Google Chrome."
            );

            return;

        }



        const recognition = new SpeechRecognition();



        let lang =
        localStorage.getItem("language") || "en";



        if(lang === "te"){

            recognition.lang = "te-IN";

        }
        else if(lang === "hi"){

            recognition.lang = "hi-IN";

        }
        else{

            recognition.lang = "en-IN";

        }



        recognition.start();



        recognition.onstart = function(){

            voiceSearchBtn.innerHTML = "🎙️";

        };



        recognition.onresult = function(event){


            let voiceText =
            event.results[0][0].transcript;



            console.log(
            "Voice:",
            voiceText
            );



            document.getElementById("searchInput").value =
            voiceText;


        };



        recognition.onerror = function(event){

            console.log(
            "Voice Error:",
            event.error
            );

        };



        recognition.onend = function(){

            voiceSearchBtn.innerHTML="🎤";

        };


    });


}





// ===============================
// 🔊 Listen Dashboard
// ===============================


const speakBtn =
document.getElementById("speakBtn");



if(speakBtn){


    speakBtn.addEventListener("click",function(){


        let container =
        document.querySelector(".container");



        if(!container){

            return;

        }



        // Stop previous speech

        window.speechSynthesis.cancel();



        let text =
        container.innerText;



        let speech =
        new SpeechSynthesisUtterance(text);



        let lang =
        localStorage.getItem("language") || "en";



        if(lang==="te"){

            speech.lang="te-IN";

        }

        else if(lang==="hi"){

            speech.lang="hi-IN";

        }

        else{

            speech.lang="en-IN";

        }



        speech.rate = 0.9;



        window.speechSynthesis.speak(speech);



    });


}