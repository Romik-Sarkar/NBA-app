/**
 * NBA Game Data Utility Functions
 * Contains functions for fetching and displaying NBA game data
 */

class GameDataManager {
    constructor() {
        this.teams = [];
        this.games = [];
        this.callbacks = {
            onGamesLoaded: [],
            onTeamsLoaded: []
        };
    }

    /**
     * Fetch teams for the dropdown
     * @returns {Promise} Promise that resolves with team data
     */
    fetchTeams() {
        return fetch('/api/teams')
            .then(response => response.json())
            .then(nbaTeams => {
                this.teams = nbaTeams;
                this._triggerCallback('onTeamsLoaded', nbaTeams);
                return nbaTeams;
            })
            .catch(error => {
                console.error('Error fetching teams:', error);
                throw error;
            });
    }

    /**
     * Fetch games for a specific date
     * @param {string} date - Date in YYYY-MM-DD format
     * @returns {Promise} Promise that resolves with game data
     */
    fetchGames(date) {
        const apiDate = formatApiDate(date);
        
        return fetch(`/api/games?date=${apiDate}`)
            .then(response => response.json())
            .then(data => {
                this.games = data.games;
                this._triggerCallback('onGamesLoaded', data.games);
                return data.games;
            })
            .catch(error => {
                console.error('Error fetching games:', error);
                throw error;
            });
    }

    /**
     * Create a game card DOM element from game data
     * @param {Object} game - Game data object
     * @returns {HTMLElement} Game card DOM element
     */
    createGameCard(game) {
        const gameCard = document.createElement('div');
        gameCard.className = 'game-card';
        gameCard.dataset.gameId = game.game_id;
        gameCard.dataset.homeTeamId = game.home_team.id;
        gameCard.dataset.visitorTeamId = game.visitor_team.id;
        
        let scoreDisplay = '';
        
        // Show score if game is in progress or final
        if (game.status.id > 1 && game.visitor_team.score !== null && game.home_team.score !== null) {
            scoreDisplay = `
                <div class="scores-container">
                    <div class="team-score visitor-score">${game.visitor_team.score}</div>
                    <div class="score-divider">-</div>
                    <div class="team-score home-score">${game.home_team.score}</div>
                </div>
            `;
        } else {
            // For upcoming games, show a "VS" indicator instead of scores
            scoreDisplay = `<div class="vs-indicator">VS</div>`;
        }
        
        // Display game status (in progress, final) or game time (if not started)
        let statusDisplay = game.status.id > 1 ? game.status.text : game.game_time;
        
        gameCard.innerHTML = `
            <div class="game-status">${statusDisplay}</div>
            <div class="teams-container">
                <div class="team visitor">
                    <div class="team-logo" data-abbr="${game.visitor_team.abbreviation}"></div>
                    <div class="team-name">${game.visitor_team.name}</div>
                </div>
                ${scoreDisplay}
                <div class="team home">
                    <div class="team-logo" data-abbr="${game.home_team.abbreviation}"></div>
                    <div class="team-name">${game.home_team.name}</div>
                </div>
            </div>
        `;
        
        return gameCard;
    }

    /**
     * Load team logos for all team logo elements on the page
     */
    loadTeamLogos() {
        // We should call this after game cards are added to the DOM
        setTimeout(() => {
            document.querySelectorAll('.team-logo').forEach(logo => {
                const teamAbbr = logo.dataset.abbr?.toLowerCase();
                
                if (!teamAbbr) return;
                
                const img = document.createElement('img');
                // Use a more reliable NBA logo source
                img.src = `https://cdn.nba.com/logos/nba/${teamAbbr}/global/L/logo.svg`;
                // Fallback to ESPN if the NBA CDN doesn't work
                img.onerror = () => {
                    img.src = `https://a.espncdn.com/i/teamlogos/nba/500/${teamAbbr}.png`;
                    
                    // If ESPN also fails, use text abbreviation
                    img.onerror = () => {
                        img.remove();
                        logo.textContent = teamAbbr.toUpperCase();
                    };
                };
                
                img.alt = `${teamAbbr.toUpperCase()} logo`;
                
                // Clear the logo container and add the image
                logo.textContent = '';
                logo.appendChild(img);
            });
        }, 500); // Small delay to ensure DOM is updated
    }

    /**
     * Filter displayed games by team
     * @param {string} teamId - Team ID or 'all' for all teams
     * @param {NodeList} gameCards - NodeList of game card elements
     * @param {HTMLElement} gamesCounter - Element to display games count
     * @param {HTMLElement} gamesGrid - Container for game cards
     * @returns {number} Number of visible games
     */
    filterGamesByTeam(teamId, gameCards, gamesCounter, gamesGrid) {
        let visibleGames = 0;

        gameCards.forEach(card => {
            const homeTeamId = card.dataset.homeTeamId;
            const visitorTeamId = card.dataset.visitorTeamId;
            const showByTeam = teamId === 'all' ||
                            teamId === homeTeamId ||
                            teamId === visitorTeamId;

            card.style.display = showByTeam ? 'block' : 'none';

            if (showByTeam) visibleGames++;
        });

        if (gamesCounter) {
            gamesCounter.textContent = `${visibleGames} game${visibleGames !== 1 ? 's' : ''}`;
        }

        if (gamesGrid) {
            const noMatchesEl = gamesGrid.querySelector('.no-matches');
            if (visibleGames === 0 && gameCards.length > 0) {
                if (!noMatchesEl) {
                    const newEl = document.createElement('div');
                    newEl.className = 'no-matches';
                    newEl.textContent = 'No games match your filters.';
                    gamesGrid.appendChild(newEl);
                }
            } else if (noMatchesEl) {
                noMatchesEl.remove();
            }
        }

        return visibleGames;
    }

    /**
     * Register a callback function
     * @param {string} event - Event name ('onGamesLoaded' or 'onTeamsLoaded')
     * @param {Function} callback - Callback function
     */
    on(event, callback) {
        if (this.callbacks[event]) {
            this.callbacks[event].push(callback);
        }
    }

    /**
     * Trigger registered callbacks
     * @private
     * @param {string} event - Event name
     * @param {any} data - Data to pass to callbacks
     */
    _triggerCallback(event, data) {
        if (this.callbacks[event]) {
            this.callbacks[event].forEach(callback => callback(data));
        }
    }
}

/**
 * Format date for API requests
 * @param {string} dateString - Date string in YYYY-MM-DD format
 * @returns {string} Formatted date string for API
 */
function formatApiDate(dateString) {
    const date = new Date(dateString);
    return date.toISOString().split('T')[0];
}

// Create and export a global instance
const gameDataManager = new GameDataManager();

// Expose functions/objects to global scope
window.gameDataManager = gameDataManager;
window.formatApiDate = formatApiDate;