from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from bs4 import BeautifulSoup
from re import match
import argparse
import requests

class ImdbRatingFetcher:
	def __enter__(self):
		options = FirefoxOptions()
		options.add_argument("--headless")
		service = Service()
		self.driver = webdriver.Firefox(service=service, options=options)
		return self

	def __exit__(self, type, value, traceback):
		self.driver.close()

	def fetch(self, userid):
		self.driver.get('https://www.imdb.com/user/%s' % userid)
		element = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'ipc-icon--star-inline')))
		data = self.driver.execute_script("return document.body.innerHTML;")
		return data

class ImdbRatingParser:
	def parse(self, content):
		soup = BeautifulSoup(content, 'html.parser')
		entries = soup.select("section[data-testid='user-ratings-feature'] div[data-testid='ratingGroup--container']")
		return [self.parse_entry(e) for e in entries]

	def parse_entry(self, entry):
		rating = int(entry.select('span span')[1].getText())
		imdb_id_url = entry.find_next_sibling("a").get('href')
		imdb_id = match(r'.*/(tt\d+)/*', imdb_id_url).group(1)
		return {'imdb_id': imdb_id, 'rating': rating}

class TmdbApi:
	def __init__(self, access_token, account_id):
		self.access_token = access_token
		self.account_id = account_id
		self.base_url = "https://api.themoviedb.org/3"

	def fetch_movie_ratings(self):
		results = self._fetch_first_page_recent(f"/account/{self.account_id}/rated/movies")
		return [movie['id'] for movie in results]

	def fetch_tvseries_ratings(self):
		results = self._fetch_first_page_recent(f"/account/{self.account_id}/rated/tv")
		return [series['id'] for series in results]

	def fetch_by_imdb_id(self, imdb_id):
		params = {
			"external_source": "imdb_id"
		}
		response = requests.get(f"{self.base_url}/find/{imdb_id}", headers=self._get_headers(), params=params)
		response.raise_for_status()
		data = response.json()

		if data.get('movie_results') and len(data['movie_results']) > 0:
			return data['movie_results'][0]['id']
		elif data.get('tv_results') and len(data['tv_results']) > 0:
			return data['tv_results'][0]['id']
		
		return None

	def add_rating(self, tmdb_id, rating):
		url = f"{self.base_url}/movie/{tmdb_id}/rating"
		headers = self._get_headers()
		payload = {
			"value": rating
		}
		response = requests.post(url, json=payload, headers=headers)
		response.raise_for_status()
		return response.json()

	def _get_headers(self):
		return {
			"Authorization": f"Bearer {self.access_token}",
			"Content-Type": "application/json;charset=utf-8"
		}

	def _fetch_first_page_recent(self, endpoint):
		params = {
			'page': 1,
			'sort_by': 'created_at.desc'
		}
		response = requests.get(f"{self.base_url}{endpoint}", headers=self._get_headers(), params=params)
		response.raise_for_status()
		data = response.json()
		return data.get('results', [])


def resolve_unrated_on_tmdb(imdb_ratings, tmdb_ratings, tmdb_api):
	result = []
	for imdb in imdb_ratings:
		tmdb_id = tmdb_api.fetch_by_imdb_id(imdb['imdb_id'])
		if not tmdb_id:
			print(f'No TMDB entry found for IMDB id {imdb["imdb_id"]}')
			continue
		if tmdb_id not in tmdb_ratings:
			result.append({'tmdb_id': tmdb_id, 'rating': imdb['rating']})
		else:
			print(f'Found one rated, everything after that should already have been synched')
			return result
	return result

def main(access_token, account_id, imdb_user_id):
	with ImdbRatingFetcher() as f:
		d = f.fetch(imdb_user_id)
		imdb_ratings = ImdbRatingParser().parse(d)

		tmdb = TmdbApi(access_token, account_id)
		tmdb_ratings = tmdb.fetch_movie_ratings() + tmdb.fetch_tvseries_ratings()

		to_be_rated = resolve_unrated_on_tmdb(imdb_ratings, tmdb_ratings, tmdb)
		for new_rating in reversed(to_be_rated):
			tmdb.add_rating(new_rating['tmdb_id'], new_rating['rating'])

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Fetch movie ratings from one IMDB and updates a TMDB rating with it")
	parser.add_argument("--access_token", required=True, help="The Bearer access token for TMDB")
	parser.add_argument("--account_id", required=True, help="The account ID for TMDB")
	parser.add_argument("--imdb_user_id", required=True, help="The user ID for IMDB (the part after /user/ in the URL)")
	args = parser.parse_args()
	main(args.access_token, args.account_id, args.imdb_user_id)