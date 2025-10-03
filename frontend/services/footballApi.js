// src/services/footballApi.js
const API_KEY = "5a5bbed8aedd9d46cc5b3dbbc249f49e";
const API_HOST = "v3.football.api-sports.io";
const LEAGUES = [61, 39, 140, 78, 135, 304, 874]; // Ligue1, Premier League, La Liga, Serie A, Bundesliga
const FREE_SEASONS = [2021, 2022, 2023]; // Free plan

const delay = (ms) => new Promise((res) => setTimeout(res, ms));

export const fetchPlayerData = async (playerName) => {
  console.log("Fetching player:", playerName);

  let player = null;

  // Step 1: Search player across all leagues

  const searchUrl = `https://${API_HOST}/players/profiles?search=${encodeURIComponent(
    playerName
  )}`;

  try {
    const resp = await fetch(searchUrl, {
      method: "GET",
      headers: { "X-RapidAPI-Key": API_KEY, "X-RapidAPI-Host": API_HOST },
    });
    const data = await resp.json();

    if (data.response && data.response.length > 0) {
      player = data.response[0].player;
      console.log("Player found:", player);
    }
  } catch (err) {
    console.error(`Error searching player :`, err);
  }

  await delay(700); // small delay

  if (!player) {
    console.log("Player not found");
    return null;
  }

  const playerId = player.id;

  // Step 2: Get all teams and seasons for this player
  let teamsData = [];
  try {
    const teamsResp = await fetch(
      `https://${API_HOST}/players/teams?player=${playerId}`,
      {
        method: "GET",
        headers: { "X-RapidAPI-Key": API_KEY, "X-RapidAPI-Host": API_HOST },
      }
    );
    const teamsJson = await teamsResp.json();
    if (teamsJson.response) {
      teamsData = teamsJson.response;
    }
  } catch (err) {
    console.error("Error fetching player teams:", err);
  }

  // Step 3: Fetch stats for each team and season
  let allStats = [];
  for (const teamItem of teamsData) {
    const teamId = teamItem.team.id;
    const seasons = teamItem.seasons.filter((s) => FREE_SEASONS.includes(s));

    for (const season of seasons) {
      const statsUrl = `https://${API_HOST}/players?id=${playerId}&team=${teamId}&season=${season}`;
      try {
        const statsResp = await fetch(statsUrl, {
          method: "GET",
          headers: { "X-RapidAPI-Key": API_KEY, "X-RapidAPI-Host": API_HOST },
        });
        const statsData = await statsResp.json();
        if (statsData.response && statsData.response.length > 0) {
          allStats.push(...statsData.response);
        }
        console.log(
          `Fetched stats: Team ${teamItem.team.name}, Season ${season}`
        );
      } catch (err) {
        console.error(
          `Error fetching stats for team ${teamItem.team.name} season ${season}:`,
          err
        );
      }
      await delay(7000); // throttle free plan
    }
  }

  const result = { player, allStats };
  console.log("Final combined player data:", result);
  return result;
};
