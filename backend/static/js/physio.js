const exercises = {
  knee: [{
    title: "Knee Bending Exercise",
    video: "/static/videos/knee/knee_bend.mp4",
    steps: "Bend and straighten your knee slowly. Repeat 10 times."
  }],
  shoulder: [{
    title: "Shoulder Roll",
    video: "/static/videos/shoulder/shoulder_roll.mp4",
    steps: "Roll shoulders forward and backward. Repeat 15 times."
  }],
  back: [{
    title: "Back Stretch",
    video: "/static/videos/back/back_stretch.mp4",
    steps: "Stretch gently and hold for 10 seconds. Repeat 5 times."
  }]
};

function loadExercises(type) {
  const area = document.getElementById("exerciseArea");
  area.innerHTML = "";

  exercises[type].forEach(ex => {
    const card = document.createElement("div");
    card.className = "exercise-card";

    card.innerHTML = `
      <video class="physio-video" controls playsinline>
        <source src="${ex.video}" type="video/mp4">
        Your browser does not support the video tag.
      </video>

      <h3>${ex.title}</h3>
      <p>${ex.steps}</p>
      <small class="warning">⚠ Stop if pain increases. Consult a physiotherapist.</small>
    `;

    area.appendChild(card);
  });
}
