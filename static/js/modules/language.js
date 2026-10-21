async function changeLanguage(lang){

    const response = await fetch(`/translations/${lang}.json`);

    const data = await response.json();

    document.querySelectorAll("[data-lang]").forEach(item=>{

        const key=item.dataset.lang;

        if(data[key]){

            item.textContent=data[key];

        }

    });

    document.querySelectorAll("[data-placeholder]").forEach(item=>{

        const key=item.dataset.placeholder;

        if(data[key]){

            item.placeholder=data[key];

        }

    });

    localStorage.setItem("language",lang);

}

const selector=document.getElementById("languageSelector");

selector.addEventListener("change",()=>{

    changeLanguage(selector.value);

});

window.onload=()=>{

    const saved=localStorage.getItem("language")||"en";

    selector.value=saved;

    changeLanguage(saved);

}      