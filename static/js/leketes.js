let score = 0;
let timeLeft = 120;
let gameInterval;
let timerInterval;
let bgAudio = new Audio("/static/sounds/2min.mp3");
let failAudio = new Audio("/static/sounds/gameover.mp3");
let winAudio = new Audio("/static/sounds/win.mp3");
let popAudio = new Audio("/static/sounds/pop.mp3");

bgAudio.volume = 0.5;
bgAudio.loop = false;
failAudio.volume = 0.9;
winAudio.volume = 0.9;
popAudio.volume = 0.6;

function startGame() {
  score = 0;
  timeLeft = 120;
  document.getElementById("leketes-score").innerText = `🏆 Σκορ: ${score}`;
  document.getElementById("leketes-timer").innerText = `⏱️ 2:00`;
  document.getElementById("leketes-area").className = "";

  bgAudio.currentTime = 0;
  bgAudio.play();

  gameInterval = setInterval(spawnBatch, 5000);
  timerInterval = setInterval(updateTimer, 1000);
}

function spawnBatch() {
  for (let i = 0; i < 5; i++) {
    spawnLekes();
  }
}

function spawnLekes() {
  const leke = document.createElement("div");
  leke.className = "leke";
  leke.style.left = Math.random() * 90 + "%";
  leke.style.top = Math.random() * 80 + "%";

  leke.onclick = () => {
    score++;
    leke.remove();
    document.getElementById("leketes-score").innerText = `🏆 Σκορ: ${score}`;
    popAudio.currentTime = 0;
    popAudio.play();
  };

  document.getElementById("leketes-area").appendChild(leke);

  setTimeout(() => {
    if (document.body.contains(leke)) {
      endGame(false);
    }
  }, 4000);
}

function updateTimer() {
  timeLeft--;
  const minutes = Math.floor(timeLeft / 60);
  const seconds = timeLeft % 60;
  document.getElementById("leketes-timer").innerText = `⏱️ ${minutes}:${seconds.toString().padStart(2, "0")}`;
  if (timeLeft <= 0) {
    endGame(true);
  }
}

function endGame(won) {
  clearInterval(gameInterval);
  clearInterval(timerInterval);
  bgAudio.pause();
  bgAudio.currentTime = 0;

  const area = document.getElementById("leketes-area");
  area.innerHTML = "";

  if (won) {
    area.classList.add("game-win");
    winAudio.play();
  } else {
    area.classList.add("game-over");
    failAudio.play();
  }

  setTimeout(() => {
    alert(`Τελικό σκορ: ${score}`);
    if (window.isAuthenticated) {
      fetch("/save-score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ score }),
      });
    }
  }, 3000);
}