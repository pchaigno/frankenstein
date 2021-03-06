#!/usr/bin/env python3
import sys
import gauss
import random
import re
import datetime
import git
import time

"""Find a streak of 50 commits in a month.

It actually searches for a streak in 29 days.
The search starts with the last commit so that the the lastest streak will be returned.
The author dates are used as reference dates.
It is possible to specify an author (via his email address) to whom all commits must belong.

Args:
	logs: The git logs as a Python array.
	author: The author for the streak or None if no author is needed.

Returns:
	The number of the last commit from the streak.
	-1 if no streak is found.
"""
def find_50commits_month(logs, author = None):
	for i in range(len(logs)-1, 50, -1):
		nb_commits = 0
		for j in range(i-1, 0, -1):
			if author != None and logs[j]['author-email'] == author:
				period = logs[i]['author-date'] - logs[j]['author-date']
				if period > 29 * 24 * 3600:
					break
				if nb_commits >= 50:
					return i
				nb_commits += 1
	return -1


"""Find a contributor who made 50 commits in a month.

Iterates on all the contributors until it finds one with 50 commits in a month.

Args:
	repository: The name of the folder where the repository is.
	logs: The git logs as a Python array.

Returns:
	A tuple with the contributor email address and the number of the last commit from the streak he made.
	A tuple with None and -1 if no contributor streak is found.
"""
def find_contributor_50commits_month(repository, logs):
	contributors = git.get_contributors(repository)
	for contributor in contributors:
		num_commit = find_50commits_month(logs, contributor)
		if num_commit != -1:
			return (contributor, num_commit)
	return (None, -1)


"""Computes the time offset to put the last commit today.

Args:
	logs: The git logs as a Python array.
	num_commit: The number of the commit we want as last.

Returns:
	The offset to apply in seconds.
"""
def compute_offset(logs, num_commit):
	return int(time.time()) - logs[num_commit]['author-date']


"""Computes the time period of the commits.

The term time designates here the time in the day.
Thus, this function finds between which hours the commits were made until now.

Args:
	logs: The git logs as a Python array.

Returns:
	A tuple with the minimum and maximum of the time period.
"""
def compute_commit_time_period(logs):
	min_time = 3600 * 24
	max_time = 0
	for i in range(0, len(logs)):
		log = logs[i]
		commit_date = datetime.datetime.fromtimestamp(log['author-date'])
		commit_time = commit_date.hour * 3600 + commit_date.minute * 60 + commit_date.second
		if commit_time > max_time:
			max_time = commit_time
		if commit_time < min_time:
			min_time = commit_time
	return (min_time, max_time)


"""Redistributes the last commits of a repository to put at least 50 of them in a month.

Selects 50 or more commits and squashes them into a month.

Args:
	logs: The git logs as a Python array.
	num_commit: The number of the last commit from the 50 we want to squash.
"""
def redistribute_commits(logs, num_commit):
	numbers_of_commits = gauss.generate_in_range(5.0/3, 29, 50, 60)
	if len(numbers_of_commits) != 29:
		raise("Incorrect number of commit numbers generated by the Gauss distribution.")
	total_commits = sum(numbers_of_commits)
	start_commit = num_commit - total_commits + 1
	end_commit = num_commit
	(min_time, max_time) = compute_commit_time_period(logs[start_commit: end_commit])
	start_date = int(time.mktime(datetime.datetime.fromtimestamp(logs[start_commit]['author-date']).date().timetuple()))
	num_commit = start_commit
	for num_day in range(0, 29):
		day = start_date + num_day * 24 * 3600
		for i in range(0, numbers_of_commits[num_day]):
			commit_time = random.randint(min_time, max_time)
			timestamp = day + commit_time
			logs[num_commit]['author-date'] = timestamp
			logs[num_commit]['committer-date'] = timestamp
			num_commit += 1


"""Try different methods to add 50 commits in a month to the user from an existing repository.

Usage: frankenstein.py <repository> <new-name> <your-email> <your-name>

Args:
	repository: The existing repository.
	new_name: The name of the repository to be created.
	your_email: The email of the user (must be linked to his GitHub account).
	your_name: The name of the user (will appear on GitHub).
"""
if __name__ == "__main__":
	if len(sys.argv) < 5:
		print("Usage: frankenstein.py <repository> <new-name> <your-email> <your-name>")
		sys.exit(2)

	source = sys.argv[1]
	new_repository = sys.argv[2]
	your_email = sys.argv[3]
	your_name = sys.argv[4]

	# If the source is an URL we need to download the repository first.
	repository = source
	matches = re.match(r'https?:\/\/.+\/([^\/]+)(\.git)?$', source)
	if matches:
		repository = git.clone_repository(source)

	# Dumps the git logs from the repository to a JSON document.
	logs = git.dump_logs(repository)

	# We only use existing commits so we need at least 50 of them:
	if len(logs) < 50:
		print("Not enough commits in this repository.")
		sys.exit(1)

	# Dumps the commits from the repository as .patch files:
	print("Dumping commits in patches...")
	git.dump_commits(repository, logs)
	print()

	# Searches for 50 commits in a month under the name of the user.
	# Only copy the repository with a time shift to put the streak in the last month if a streak is found.
	print("Checking if you made 50 commits in a month...")
	num_commit = find_50commits_month(logs, your_email)
	if num_commit != -1:
		print("You made 50 commits in a month with %dth as last commit" % (num_commit))
		offset = compute_offset(logs, num_commit)
		git.rebuild_repository(repository, logs, new_repository, your_name, your_email, [], offset)
		sys.exit(0)
	print()

	# Searches for a contributor with 50 commits in a month.
	# If found, the contributor will be replaced with the user of the script.
	# During the copy the date will be shifted as before.
	print("Searching for a contributor with 50 commits in a month...")
	(contributor, num_commit) = find_contributor_50commits_month(repository, logs)
	if contributor != None:
		print("%s made 50 commits in a month with %dth as last commit" % (contributor, num_commit))
		offset = compute_offset(logs, num_commit)
		git.rebuild_repository(repository, logs, new_repository, your_name, your_email, [contributor], offset)
		sys.exit(0)
	print()

	# Searches for a month with 50 commits.
	# If found, all contributors to the project will be replaced with the user of the script.
	# Then, the date will be shifted during the copy as before.
	print("Searching for a month with 50 commits...")
	num_commit = find_50commits_month(logs)
	if num_commit != -1:
		print("50 commits in a month were found ending with commit %d" % (num_commit))
		offset = compute_offset(logs, num_commit)
		git.rebuild_repository(repository, logs, new_repository, your_name, your_email, 'all', offset)
		sys.exit(0)
	print()

	# Squashes 50 or more commit dates to put them in a month.
	# Then, the date are shifted as before to put the 50 squashed commits in the last month.
	last_commit = len(logs) - 1
	redistribute_commits(logs, last_commit)
	offset = compute_offset(logs, last_commit)
	git.rebuild_repository(repository, logs, new_repository, your_name, your_email, 'all', offset)
	sys.exit(0)
