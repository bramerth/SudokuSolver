#!/usr/bin/python
# -*- coding: UTF-8 -*-
import argparse
import BeautifulSoup
import copy
import sys
import time
import urllib2
from collections import defaultdict, Counter

class SudokuCell(object):
	def __init__(self, value, coords):
		self.value = value
		self.coords = coords
		self.potential_values = []
		self.row = None
		self.column = None
		self.box = None

	def update_potential_values(self):
		if self.value is None:
			self.potential_values = [c for c in "123456789"]
			for group in (self.row, self.column, self.box):
				for cell in group:
					if cell.value in self.potential_values:
						self.potential_values.remove(cell.value)
		else:
			self.potential_values = [self.value]

	def neighbors(self):
		cells = set()
		for group in (self.row, self.column, self.box):
			for cell in group:
				cells.add(cell)
		return cells

	def __str__(self):
		return "-" if self.value is None else self.value

class SudokuCellGroup(object):
	def __init__(self, cells):
		self._cells = cells

	def __iter__(self):
		return iter(self._cells)

	def __str__(self):
		return ",".join(str(c) for c in self._cells)

class SudokuBoard(object):
		
	def __init__(self):
		self._matrix = []

	@staticmethod
	def create_with_file(path):
		board = SudokuBoard()
		with open(path, "r") as f:
			lines = f.readlines()
			for i, line in enumerate(lines):
				line = line.strip()
				if len(line) == 0:
					continue
				row = [SudokuCell(c if c is not "-" else None, (i, j)) for j, c in enumerate(line)]
				if len(row) != 9:
					raise ValueError("invalid column count")
				board._matrix.append(row)
			if len(board._matrix) != 9:
				raise ValueError("invalid row count")
		board._init_cells()
		return board

	@staticmethod
	def create_from_web_sudoku(level):
		board = SudokuBoard()
		url = "http://backup.websudoku.com/?level={}".format(level)
		soup = BeautifulSoup.BeautifulSoup(urllib2.urlopen(url).read())
		
		puzzle_cells = soup.findAll("input", attrs={"id":"cheat"})[0]["value"]
		mask_cells = soup.findAll("input", attrs={"id":"editmask"})[0]["value"]
		seq = [c if m == "0" else None for c, m in zip(puzzle_cells, mask_cells)]		
		if len(seq) != 81:
			raise ValueError("invalid puzzle data")

		for i in range(0, 9):
			row = [SudokuCell(c, (i, j)) for j, c in enumerate(seq[i * 9:(i + 1) * 9])]
			board._matrix.append(row)
		board._init_cells()
		return board

	def clone(self):
		c = SudokuBoard()
		c._matrix = copy.deepcopy(self._matrix)
		return c

	def _init_cells(self):
		for row in self.rows():
			for cell in row:
				cell.row = row
		for col in self.columns():
			for cell in col:
				cell.column = col
		for box in self.boxes():
			for cell in box:
				cell.box = box

	def is_legal(self):
		for groups in (self.rows(), self.columns(), self.boxes()):
			for group in groups:
				value_counter = Counter(c.value for c in group if c.value is not None)
				if any(value != 1 for value in value_counter.values()):
					return False
		return True

	def cell(self, coords):
		return self._matrix[coords[0]][coords[1]]

	def solved(self):
		return all(c.value is not None for c in self.cells())

	def cells(self):
		return (cell for row in self._matrix for cell in row)

	def rows(self):
		return (SudokuCellGroup(row) for row in self._matrix)

	def columns(self):
		return (SudokuCellGroup([self._matrix[i][j] for i in range(9)]) for j in range(9))

	def boxes(self):
		for i in range(0, 9, 3):
			for j in range(0, 9, 3):
				yield SudokuCellGroup([self._matrix[k][l] for k in range(i, i+3) for l in range(j, j+3)])

	def __str__(self):
		return "\n".join("".join(str(c) for c in row) for row in self.rows())

def solve1(board, inference_depth, verbose):
	# Solve any cells for which there is only one potential value.
	solved_cell = None
	for cell in board.cells():
		cell.update_potential_values()
		if cell.value is None and len(cell.potential_values) == 1:
			solved_cell = cell
			solved_cell.value = solved_cell.potential_values[0]
			if verbose:
				sys.stderr.write("{}solving {} as {} (only potential value)\n".format("  " * inference_depth, solved_cell.coords, solved_cell.value))
			for cell in solved_cell.neighbors():
				cell.update_potential_values()
	return solved_cell is not None

def solve2(board, inference_depth, verbose):
	# Solve any cells for which one of the potential values is unique within its group.
	solved_cell = None
	for groups in (board.rows(), board.columns(), board.boxes()):
		for group in groups:
			cells_with_potential_values = defaultdict(list)
			for cell in group:
				if cell.value is None:
					for val in cell.potential_values:
						cells_with_potential_values[val].append(cell)
			for val in cells_with_potential_values:
				if len(cells_with_potential_values[val]) == 1:
					solved_cell = cells_with_potential_values[val][0]
					solved_cell.value = val
					if verbose:
						sys.stderr.write("{}solving {} as {} (potential value is unique in group)\n".format("  " * inference_depth, solved_cell.coords, solved_cell.value))
					for cell in solved_cell.neighbors():
						cell.update_potential_values()
	return solved_cell is not None

def solve3(board, inference_depth, verbose):
	# Try both values for any cells that have two potential values and attempt to solve the puzzle for each resulting board.
	for cell in board.cells():
		if cell.value is None and len(cell.potential_values) == 2:
			state1 = board.clone()
			state2 = board.clone()
			state1.cell(cell.coords).value = cell.potential_values[0]
			state2.cell(cell.coords).value = cell.potential_values[1]
			if verbose:
				sys.stderr.write("{}guessing {} as {}\n".format("  " * inference_depth, cell.coords, cell.potential_values[0]))
			board, solved = solve(state1, inference_depth + 1, verbose)
			if solved:
				return board, True
			if verbose:
				sys.stderr.write("{}guessing {} as {}\n".format("  " * inference_depth, cell.coords, cell.potential_values[1]))
			board, solved = solve(state2, inference_depth + 1, verbose)
			if solved:
				return board, True
			if inference_depth > 0:
				return board, False
	if verbose:
		sys.stderr.write("{}board has no solution!\n".format("  " * inference_depth))
	return board, False

def solve(board, inference_depth=0, verbose=False):
	solved_cell = True
	while not board.solved() and solved_cell:
		while solved_cell:
			solved_cell = solve1(board, inference_depth, verbose)
		solved_cell = solve2(board, inference_depth, verbose)

	if not board.solved():
		return solve3(board, inference_depth, verbose)
	else:
		return board, True

def parse_arguments():
	parser = argparse.ArgumentParser(description='Solve Sudoku puzzles')
	parser.add_argument('file', help='a file representing game state', nargs="?")
	parser.add_argument('--level', help='a difficulty level (for websudoku.com puzzles)', default="4", choices=["1", "2", "3", "4"])
	parser.add_argument('-v-', '--verbose', action="store_true", help='print debug information while solving')
	args = vars(parser.parse_args())
	return args

def main():
	args = parse_arguments()
	if args["file"]:
		board = SudokuBoard.create_with_file(args["file"])
	else:
		board = SudokuBoard.create_from_web_sudoku(args["level"])
	assert board.is_legal()

	print "Starting board:"
	print board
	print
	
	start = time.time()
	board, solved = solve(board, verbose=args["verbose"])
	elapsed = time.time() - start
	assert board.is_legal()


	if solved:
		print "Solved!"
	else:
		print "Board has no solution!"
	print board
	print
	print "Time elapsed: %f" % elapsed


if __name__ == '__main__':
	main()
