import sys
from collections import namedtuple, defaultdict
from json import dump

GameState = namedtuple('GameState', ['board', 'location', 'orientation', 'arrow', 'alive', 'won', 'wumpus_dead'])
Point = namedtuple('Point', ['row', 'col'])

danger_map = {
    'S': 'Wumpus',
    'B': 'Pit',
}

def parse_board(string):
    """Returns initial grid that is created from the input file."""
    lines = string.strip().split('\n')
    return reorient([ line.replace(' ', '').split(',') for line in lines ])

def reorient(board):
    # He wants the board to be indexed in a very stupid way.
    # This makes that work.
    return list(map(list, zip(*list(reversed(board)))))

def adjacent_points(board, point):
    """Returns a list of squares adjacent to a set of coordinates."""
    offsets = [(0,1), (0, -1), (1, 0), (-1, 0)]
    rows = len(board)
    cols = len(board[0])
    points = [
        Point(point.row + row_offset, point.col + col_offset)
        for row_offset, col_offset in offsets
    ]
    return [
        point for point in points
        if 0 <= point.row < rows
        and 0 <= point.col < cols
    ]

def adjacent_values(board, point):
    """Returns the values on the board that are adjacent to a point."""
    return [board[p.row][p.col] for p in adjacent_points(board, point)]

def get_percepts(board, point):
    """Returns a tuple of the percepts present at a point"""
    adj = adjacent_values(board, point)
    percepts = []
    if 'W' in adj:
        percepts.append('S')
    if 'P' in adj:
        percepts.append('B')
    if board[point.row][point.col] == 'G':
        percepts.append('G')
    return tuple(percepts)

def get_danger_percepts(board, point):
    percepts = get_percepts(board, point)
    return set(percepts) & set(danger_map.keys())

def convert_orientation(orientation):
    """Returns the long form of orientation for printing to console."""
    mapping = { 'E':'EAST', 'W':'WEST', 'N':'NORTH', 'S':'SOUTH'}
    return mapping[orientation]

def print_location(game):
    """Prints the location of the player to the console."""
    print("You are in room ({},{}) of the cave. Facing {}.".format(
        game.location.row+1, game.location.col+1, 
        convert_orientation(game.orientation)))

def print_percepts(game):
    """Prints the percepts of a location to the console."""
    for percept in get_percepts(game.board, game.location):
        if percept == 'S' and not game.wumpus_dead:
            print("It's stinky in here!")
        elif percept == 'B':
            print("You feel a breeze in this room.")
        elif percept == 'G':
            print('Something glitters at your feet!')

def print_hints(game, kb):
    certain_hints, maybe_hints = kb.get_hints()
    for percept, points in certain_hints.items():
        danger = danger_map[percept]
        for point in points:
            print("HINT: There is a {} at {},{}".format(danger, 
                point[0]+1, point[1]+1))
    for percept, points in maybe_hints.items():
        danger = danger_map[percept]
        for point in points:
            print("HINT: There may be a {} at {},{}".format(danger, 
                point[0]+1, point[1]+1))

def left_command(game):
    """Changes orientation by turning R."""
    cycle = ['N','W','S','E','N']
    return game._replace(
        orientation=cycle[cycle.index(game.orientation) + 1])

def right_command(game):
    """Changes orientation by turning R."""
    cycle = ['N','E','S','W','N']
    return game._replace(
        orientation=cycle[cycle.index(game.orientation) + 1])

def possible_moves(game):
    """Returns a list of moves that will not make the player bump into a wall."""
    directions = ('N','S','E','W')
    i,j = game.location.row, game.location.col
    points = [Point(i,j+1), Point(i,j-1), Point(i+1,j), Point(i-1,j)]
    return { direction:point for direction,point in zip(directions,points)
            if 0 <= point.row < len(game.board) and
            0 <= point.col < len(game.board[0]) }

def forward_command(game):
    """Goes one square forward."""
    moves = possible_moves(game)
    if game.orientation not in moves:
        print('BUMP!!! You hit a wall!')
        return game
    else:
        return move(game,moves)
    
def move(game, moves):
    """Move Forward Helper checks conditions and adjusts game status accordingly."""
    i = moves[game.orientation].row
    j = moves[game.orientation].col

    game = game._replace(location=Point(i, j))

    if game.board[i][j] == 'P':
        print('You have fallen into the pit!!!')
        return game._replace(alive=False)

    elif game.board[i][j] == 'W':
        if not game.wumpus_dead:
            print('You have been eaten by the Wumpus!!!')
            return game._replace(alive=False)

        print('A dead wumpus lays at your feet. You hold your bow triumphantly aloft.')
        return game

    elif game.board[i][j] == 'G':
        print('You have found the gold and won the game!!!')
        return game._replace(won=True)

    else:
        return game

def shoot_arrow(game, kb):
    """Returns a T or F, depending on whether the player successfully kills the Wumpus."""

    arrow_room = game.location

    moving_game = game
    while game.orientation in possible_moves(moving_game):
        arrow_room = possible_moves(moving_game)[game.orientation]
        if game.board[arrow_room.row][arrow_room.col] == 'W':
            return True, arrow_room
        moving_game = moving_game._replace(location=arrow_room)

    return False, None

def execute_command(command, game, kb):
    """Executes the command that the player has chosen."""
    if command == 'R':
        return right_command(game)
        
    elif command == 'L':
        return left_command(game)

    elif command == 'F':
        return forward_command(game)

    else:
        if game.arrow:
            hit, loc = shoot_arrow(game, kb)
            if hit:
                print('You hear a loud scream!!! The Wumpus is dead!!!')


                # update the knowledge base
                danger_map['S'] = 'dead Wumpus'
                kb.wumpus_dead = True

                return game._replace(
                    wumpus_dead=True,
                    arrow=False)
            else:
                print('Your arrow did not hit the Wumpus!!!')
                return game._replace(
                    arrow=False)
        else:
            print('You have already used your only arrow!!!')
            return game

def main(filename):
    # read the file in as a string and parse into a board
    input_string = open(filename).read()
    board = parse_board(input_string)

    if len(board) == 0:
        print('Invalid board! no rows')
        return
    if not all(len(row) == len(board[0]) for row in board):
        print('Invalid board! all rows should have same length')
        return
    
    # Set up intial state of game
    game = GameState(
        board=board,
        location=Point(0,0),
        orientation='E',
        arrow=True,
        alive=True,
        won=False,
        wumpus_dead=False)
    valid_commands = ('R','L','F','S')

    # Prepare the knowledge base
    rows = len(board)
    cols = len(board[0])
    kb = KnowledgeBase((rows, cols))

    while game.alive and not game.won:

        # Update the knowledge base.
        percepts = get_danger_percepts(game.board, game.location)
        kb.add_observation(tuple(game.location), percepts)
        write_kb_to_file(kb, 'kb.dat')

        print_location(game)
        print_percepts(game)
        print_hints(game, kb)

        command = input("What would you like to do? Please enter command [R,L,F,S]:\n").strip().upper()

        if command not in valid_commands:
            print('Invalid command! Please choose from [R,L,F,S]!\n')
            continue

        game = execute_command(command, game, kb)

    
    sys.exit('Thanks for playing Wumpus World!!!')

class KnowledgeBase:
    """Knowledge base for the Hunt of the Wumpus.

    Set up the knowledge base by giving it the dimensions of your grid.

    >>> kb = KnowledgeBase((4,4))

    Add perceptions from each point you visit.

    >>> kb.add_observation((0,0) {})
    >>> kb.add_observation((1,0) {'Breezy'})
    >>> kb.add_observation((0,1) {'Stinky'})

    Then, you can get hints!

    >>> certain_hints, maybe_hints = kb.get_hints()
    >>> maybe_hints
    {}
    >>> certain_hints
    {'Breezy': {(2, 0)}, 'Stinky': {(0, 2)}}

    """

    def __init__(self, dimensions):
        self.dimensions = dimensions
        self.visited = {}
        self.wumpus_dead = False

    def add_observation(self, point, percepts):
        """Load an observation into the knowledge base.

        Arguments:
        point: a tuple with coordinates of the observed point
        percepts: a set of percepts noted at this point

        """
        self.visited[point] = percepts

    def intersect_map(self):
        intersect_map = defaultdict(set)
        for percept_point, percepts in self.visited.items():
            for point in self.get_adjacent(percept_point):
                if point in self.visited:
                    continue
                if point not in intersect_map:
                    intersect_map[point] = set(percepts)
                else:
                    intersect_map[point] &= set(percepts)
        for point in list(intersect_map.keys()):
            if len(intersect_map[point]) == 0:
                del intersect_map[point]
        return dict(intersect_map)

    def get_hints(self):
        intersect_map = self.intersect_map()
        certain_hints = defaultdict(set)
        maybe_hints = defaultdict(set)
        for percept_point, percepts in self.visited.items():
            for percept in percepts:
                if percept == 'S' and self.wumpus_dead:
                    continue
                possible_points = set()
                for point in self.get_adjacent(percept_point):
                    if percept in intersect_map.get(point, []):
                        possible_points.add(point)
                assert len(possible_points) != 0, (
                        "percept {} at {} must have source"
                            .format(percept, percept_point))
                if len(possible_points) == 1:
                    certain_hints[percept] |= possible_points
                else:
                    maybe_hints[percept] |= possible_points
        # If we're certain, there's no maybe about it.
        for percept, points in certain_hints.items():
            if percept in maybe_hints:
                for point in points:
                    maybe_hints[percept].discard(point)
        return dict(certain_hints), dict(maybe_hints)

    def get_observations(self):
        return self.visited

    def get_adjacent(self, point):
        return get_adjacent(point, self.dimensions)

def get_adjacent(point, dimensions=None):
    if dimensions and len(dimensions) != len(point):
        raise ValueError('invalid point')
    adjacent = set()
    for ii in range(len(point)):
        coord = point[ii]
        for modifier in (1, -1):
            value = coord + modifier
            if not dimensions or 0 <= value < dimensions[ii]:
                adjacent.add(tuple(point[:ii] + (value,) + point[ii+1:]))
    return adjacent

def write_kb_to_file(kb, filename):
    tos = lambda d: {str(k):str(v) for k,v in d.items()}
    certain_hints, maybe_hints = kb.get_hints()
    obj = {
        'observations': tos(kb.get_observations()),
        'known_locations': dict((danger_map[k], str(v)) for k,v in certain_hints.items()),
        'possible_locations': dict((danger_map[k], str(v)) for k,v in maybe_hints.items()),
        'intersect_map': tos(kb.intersect_map()),
        'wumpus_alive': kb.wumpus_dead,
    }
    with open(filename, 'w') as fp:
        dump(obj, fp)

if __name__ == '__main__':

    if len(sys.argv) != 2:
        sys.exit('Please include a filename! We must have that to generate the board!')
  
    filename = sys.argv[1]
    main(filename)
