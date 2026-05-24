#!/usr/bin/env python3
import argparse
import json
import requests


def fetch_rated_movies(access_token, account_id):
	base_url = "https://api.themoviedb.org/3"
	rated_movies = []
	page = 1
	headers = {
		"Authorization": f"Bearer {access_token}"
	}

	while True:
		url = f"{base_url}/account/{account_id}/rated/movies"
		params = {
			"page": page,
			"sort_by": "created_at.asc"
		}

		response = requests.get(url, params=params, headers=headers)
		response.raise_for_status()
		data = response.json()

		rated_movies.extend(data.get("results", []))

		total_pages = data.get("total_pages", 1)
		print(f"Fetched page {page} of {total_pages}")

		if page >= total_pages:
			break

		page += 1

	return rated_movies


def fetch_movie_details(access_token, movie_id):
	url = f"https://api.themoviedb.org/3/movie/{movie_id}"
	headers = {
		"Authorization": f"Bearer {access_token}"
	}

	response = requests.get(url, headers=headers)
	response.raise_for_status()
	return response.json()


def normalize_country_codes(country_codes):
	country_mapping = {
		"HK": ["CN"],  # Hong Kong -> China, because the map I'm using doesn't handle them
		"TW": ["CN"],  # Taiwan -> China, because the map I'm using doesn't handle them
		"YU": ["RS", "HR", "BA", "SI", "MK", "ME", "XK"]  # Yugoslavia -> successor states
	}
	
	normalized = []
	for country in country_codes:
		if country in country_mapping:
			normalized.extend(country_mapping[country])
		else:
			normalized.append(country)
	
	return normalized

def parse_countries(movie_details):
	origin_country = movie_details.get("origin_country")

	if origin_country:
		return normalize_country_codes(origin_country)
	else:
		return ["UNKNOWN"]

def get_ratings_by_country(access_token, account_id):
	rated_movies = fetch_rated_movies(access_token, account_id)
	country_stats = {}
	total_movies = len(rated_movies)

	for index, movie in enumerate(rated_movies, 1):
		movie_id = movie.get("id")
		movie_title = movie.get("title", "Unknown")

		print(f"Fetching details for movie {index} of {total_movies}: {movie_title}")
		movie_details = fetch_movie_details(access_token, movie_id)

		country_codes = parse_countries(movie_details)

		is_solo = len(country_codes) == 1

		for country_code in country_codes:
			if country_code not in country_stats:
				country_stats[country_code] = {
					"solo": 0,
					"group": 0,
					"movies": []
				}

			if is_solo:
				country_stats[country_code]["solo"] += 1
			else:
				country_stats[country_code]["group"] += 1
			country_stats[country_code]["movies"].append({"id": movie_id, "title": movie_title})

	return country_stats


def main():
	parser = argparse.ArgumentParser(description="Fetch movie ratings from TMDB and aggregate by production country")
	parser.add_argument("--access_token", required=True, help="The Bearer access token for TMDB")
	parser.add_argument("--account_id", required=True, help="The account ID for TMDB")
	parser.add_argument("--target", required=True, help="The target file to write the result to")

	args = parser.parse_args()

	try:
		print(f"Fetching ratings for account {args.account_id}")
		ratings_by_country = get_ratings_by_country(args.access_token, args.account_id)

		# Write results to target file
		with open(args.target, "w") as f:
			json.dump(ratings_by_country, f, indent=4)

		print(f"Successfully wrote results to {args.target}")
	except Exception as e:
		print(f"Error: {e}")
		return 1

	return 0


if __name__ == "__main__":
	exit(main())
