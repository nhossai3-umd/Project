"""
test_trackbook.py

Unit tests for the Trackbook application.

Tests cover:
  - Textbook and Listing dataclass methods (textbook.py)
  - Input validation and search logic (search.py)
  - Watchlist data handling and serialization (data_handler.py)
  - Display formatting helpers (display.py)

Any function that performs direct console I/O (print/input) is instead
covered by the written testing procedure at the bottom of this file.

Run tests with:
    python -m pytest test_trackbook.py -v
or:
    python test_trackbook.py

Author: Trackbook Team
"""

import unittest
import os
import json

from textbook import Textbook, Listing
from search import (
    is_valid_isbn,
    normalize_isbn,
    validate_input,
    search_by_isbn,
    search_by_title,
    search,
)
from data_handler import (
    add_to_watchlist,
    remove_from_watchlist,
    is_in_watchlist,
    save_watchlist,
    load_watchlist,
    _serialize_listing,
    _deserialize_listing,
    _serialize_watchlist,
    _deserialize_watchlist,
)
from display import _divider, _table_header, _listing_row


# ---------------------------------------------------------------------------
# Helpers: reusable sample objects
# ---------------------------------------------------------------------------

def make_listing(source="Amazon", price=29.99, condition="Good",
                 url="https://example.com", timestamp="2025-04-01") -> Listing:
    """Return a Listing with default or supplied values."""
    return Listing(source=source, price=price, condition=condition,
                   url=url, timestamp=timestamp)


def make_textbook(title="Test Book", isbn="978-0000000001",
                  author="Test Author") -> Textbook:
    """Return a Textbook with no listings by default."""
    return Textbook(title=title, isbn=isbn, author=author)


# ===========================================================================
# Tests: Listing
# ===========================================================================

class TestListing(unittest.TestCase):
    """Tests for the Listing dataclass."""

    def test_listing_fields_stored_correctly(self):
        """Listing stores all five fields exactly as provided."""
        lst = Listing("eBay", 15.00, "Acceptable", "https://ebay.com", "2025-01-01")
        self.assertEqual(lst.source, "eBay")
        self.assertEqual(lst.price, 15.00)
        self.assertEqual(lst.condition, "Acceptable")
        self.assertEqual(lst.url, "https://ebay.com")
        self.assertEqual(lst.timestamp, "2025-01-01")

    def test_listing_default_timestamp_is_today(self):
        """Listing without explicit timestamp defaults to today's date (non-empty string)."""
        lst = Listing("Amazon", 10.00, "Good", "https://amazon.com")
        self.assertIsInstance(lst.timestamp, str)
        self.assertGreater(len(lst.timestamp), 0)

    def test_listing_str_contains_source_and_price(self):
        """__str__ output includes the source name and formatted price."""
        lst = make_listing(source="Chegg", price=49.99)
        result = str(lst)
        self.assertIn("Chegg", result)
        self.assertIn("49.99", result)


# ===========================================================================
# Tests: Textbook
# ===========================================================================

class TestTextbook(unittest.TestCase):
    """Tests for the Textbook dataclass and its methods."""

    def setUp(self):
        """Set up a Textbook with three listings for use in each test."""
        self.book = make_textbook()
        self.book.add_listing(make_listing("Amazon",   50.00, "New"))
        self.book.add_listing(make_listing("eBay",     20.00, "Good"))
        self.book.add_listing(make_listing("AbeBooks", 35.00, "Acceptable"))

    # --- add_listing ---

    def test_add_listing_increases_count(self):
        """add_listing should increase the listings count by 1."""
        book = make_textbook()
        self.assertEqual(len(book.listings), 0)
        book.add_listing(make_listing())
        self.assertEqual(len(book.listings), 1)

    def test_add_multiple_listings(self):
        """Adding multiple listings stores all of them."""
        self.assertEqual(len(self.book.listings), 3)

    # --- get_lowest_price ---

    def test_get_lowest_price_returns_correct_listing(self):
        """get_lowest_price returns the listing with the smallest price."""
        lowest = self.book.get_lowest_price()
        self.assertEqual(lowest.price, 20.00)
        self.assertEqual(lowest.source, "eBay")

    def test_get_lowest_price_empty_book_returns_none(self):
        """get_lowest_price on a book with no listings returns None."""
        empty_book = make_textbook()
        self.assertIsNone(empty_book.get_lowest_price())

    def test_get_lowest_price_single_listing(self):
        """get_lowest_price with one listing returns that listing."""
        book = make_textbook()
        lst = make_listing(price=99.99)
        book.add_listing(lst)
        self.assertEqual(book.get_lowest_price(), lst)

    # --- get_listings_by_condition ---

    def test_filter_by_condition_match(self):
        """get_listings_by_condition returns only listings matching the condition."""
        results = self.book.get_listings_by_condition("Good")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source, "eBay")

    def test_filter_by_condition_case_insensitive(self):
        """get_listings_by_condition is case-insensitive."""
        results_lower = self.book.get_listings_by_condition("good")
        results_upper = self.book.get_listings_by_condition("GOOD")
        self.assertEqual(len(results_lower), 1)
        self.assertEqual(len(results_upper), 1)

    def test_filter_by_condition_no_match(self):
        """get_listings_by_condition returns empty list when no match found."""
        results = self.book.get_listings_by_condition("Like New")
        self.assertEqual(results, [])

    def test_filter_by_condition_multiple_matches(self):
        """get_listings_by_condition returns all matching listings."""
        self.book.add_listing(make_listing("Chegg", 30.00, "Good"))
        results = self.book.get_listings_by_condition("Good")
        self.assertEqual(len(results), 2)

    # --- get_listings_by_source ---

    def test_filter_by_source_match(self):
        """get_listings_by_source returns only listings from the given source."""
        results = self.book.get_listings_by_source("Amazon")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].price, 50.00)

    def test_filter_by_source_case_insensitive(self):
        """get_listings_by_source is case-insensitive."""
        results = self.book.get_listings_by_source("amazon")
        self.assertEqual(len(results), 1)

    def test_filter_by_source_no_match(self):
        """get_listings_by_source returns empty list when source not found."""
        results = self.book.get_listings_by_source("Facebook Marketplace")
        self.assertEqual(results, [])

    # --- get_listings_under_price ---

    def test_filter_under_price_includes_equal(self):
        """get_listings_under_price includes listings exactly equal to max_price."""
        results = self.book.get_listings_under_price(20.00)
        prices = [lst.price for lst in results]
        self.assertIn(20.00, prices)

    def test_filter_under_price_excludes_above(self):
        """get_listings_under_price excludes listings above max_price."""
        results = self.book.get_listings_under_price(30.00)
        for lst in results:
            self.assertLessEqual(lst.price, 30.00)

    def test_filter_under_price_zero_returns_empty(self):
        """get_listings_under_price with $0 max returns no listings (all > 0)."""
        results = self.book.get_listings_under_price(0.00)
        self.assertEqual(results, [])

    def test_filter_under_price_high_threshold_returns_all(self):
        """get_listings_under_price with very high max returns all listings."""
        results = self.book.get_listings_under_price(10000.00)
        self.assertEqual(len(results), len(self.book.listings))

    # --- sort_listings_by_price ---

    def test_sort_listings_by_price_ascending(self):
        """sort_listings_by_price returns listings in ascending order."""
        sorted_listings = self.book.sort_listings_by_price()
        prices = [lst.price for lst in sorted_listings]
        self.assertEqual(prices, sorted(prices))

    def test_sort_listings_does_not_modify_original(self):
        """sort_listings_by_price returns a new list, not modifying self.listings."""
        original_order = [lst.price for lst in self.book.listings]
        self.book.sort_listings_by_price()
        current_order = [lst.price for lst in self.book.listings]
        self.assertEqual(original_order, current_order)

    def test_sort_listings_empty_book(self):
        """sort_listings_by_price on empty book returns empty list."""
        book = make_textbook()
        self.assertEqual(book.sort_listings_by_price(), [])

    # --- __str__ ---

    def test_textbook_str_contains_title_and_isbn(self):
        """Textbook __str__ includes the title and ISBN."""
        result = str(self.book)
        self.assertIn("Test Book", result)
        self.assertIn("978-0000000001", result)


# ===========================================================================
# Tests: search.py — validation and lookup
# ===========================================================================

class TestIsValidIsbn(unittest.TestCase):
    """Tests for is_valid_isbn."""

    def test_valid_isbn13_with_hyphens(self):
        """13-digit ISBN with hyphens is valid."""
        self.assertTrue(is_valid_isbn("978-0134444321"))

    def test_valid_isbn13_no_hyphens(self):
        """13-digit ISBN without hyphens is valid."""
        self.assertTrue(is_valid_isbn("9780134444321"))

    def test_valid_isbn10(self):
        """10-digit ISBN is valid."""
        self.assertTrue(is_valid_isbn("0134444321"))

    def test_invalid_isbn_too_short(self):
        """ISBN with fewer than 10 digits is invalid."""
        self.assertFalse(is_valid_isbn("12345"))

    def test_invalid_isbn_too_long(self):
        """ISBN with more than 13 digits is invalid."""
        self.assertFalse(is_valid_isbn("12345678901234"))

    def test_invalid_isbn_11_digits(self):
        """11-digit number is not a valid ISBN length."""
        self.assertFalse(is_valid_isbn("12345678901"))

    def test_invalid_isbn_contains_letters(self):
        """ISBN with non-digit characters (other than hyphens) is invalid."""
        self.assertFalse(is_valid_isbn("978-ABC123456"))

    def test_isbn_with_spaces(self):
        """ISBN with spaces instead of hyphens is normalized and validated."""
        self.assertTrue(is_valid_isbn("978 0134444321"))


class TestNormalizeIsbn(unittest.TestCase):
    """Tests for normalize_isbn."""

    def test_removes_hyphens(self):
        """normalize_isbn strips hyphens."""
        self.assertEqual(normalize_isbn("978-0134444321"), "9780134444321")

    def test_removes_spaces(self):
        """normalize_isbn strips spaces."""
        self.assertEqual(normalize_isbn("978 0134 4443 21"), "9780134444321")

    def test_plain_digits_unchanged(self):
        """normalize_isbn leaves a plain digit string unchanged."""
        self.assertEqual(normalize_isbn("9780134444321"), "9780134444321")


class TestValidateInput(unittest.TestCase):
    """Tests for validate_input."""

    def test_valid_title(self):
        """A normal title string is valid."""
        valid, msg = validate_input("Python Programming")
        self.assertTrue(valid)
        self.assertEqual(msg, "")

    def test_valid_isbn(self):
        """An ISBN string is accepted as a valid query."""
        valid, msg = validate_input("978-0134444321")
        self.assertTrue(valid)

    def test_empty_string_is_invalid(self):
        """An empty string fails validation."""
        valid, msg = validate_input("")
        self.assertFalse(valid)
        self.assertNotEqual(msg, "")

    def test_whitespace_only_is_invalid(self):
        """A whitespace-only string fails validation."""
        valid, msg = validate_input("   ")
        self.assertFalse(valid)

    def test_single_character_is_invalid(self):
        """A single character fails the minimum length check."""
        valid, msg = validate_input("A")
        self.assertFalse(valid)

    def test_two_characters_is_valid(self):
        """Two characters is the minimum valid length."""
        valid, msg = validate_input("AB")
        self.assertTrue(valid)


class TestSearchFunctions(unittest.TestCase):
    """Tests for search_by_isbn, search_by_title, and search."""

    def test_search_by_isbn_found(self):
        """search_by_isbn returns the correct Textbook for a known ISBN."""
        result = search_by_isbn("978-0134444321")
        self.assertIsNotNone(result)
        self.assertEqual(result.isbn, "978-0134444321")

    def test_search_by_isbn_normalized(self):
        """search_by_isbn works when hyphens are removed from the query."""
        result = search_by_isbn("9780134444321")
        self.assertIsNotNone(result)

    def test_search_by_isbn_not_found(self):
        """search_by_isbn returns None for an unknown ISBN."""
        result = search_by_isbn("978-9999999999")
        self.assertIsNone(result)

    def test_search_by_title_exact_match(self):
        """search_by_title returns a result for an exact title match."""
        result = search_by_title("Intro to Python Programming")
        self.assertIsNotNone(result)
        self.assertIn("Python", result.title)

    def test_search_by_title_case_insensitive(self):
        """search_by_title is case-insensitive."""
        result = search_by_title("intro to python programming")
        self.assertIsNotNone(result)

    def test_search_by_title_partial_match(self):
        """search_by_title returns a result for a partial title match."""
        result = search_by_title("Effective Java")
        self.assertIsNotNone(result)

    def test_search_by_title_not_found(self):
        """search_by_title returns None for an unknown title."""
        result = search_by_title("Calculus for Engineers")
        self.assertIsNone(result)

    def test_search_detects_isbn(self):
        """search() routes to ISBN lookup when input is a valid ISBN."""
        result = search("978-0134444321")
        self.assertIsNotNone(result)
        self.assertEqual(result.isbn, "978-0134444321")

    def test_search_detects_title(self):
        """search() routes to title lookup when input is not an ISBN."""
        result = search("Effective Java")
        self.assertIsNotNone(result)

    def test_search_unknown_returns_none(self):
        """search() returns None for a query that matches nothing."""
        result = search("Zoology for Martians")
        self.assertIsNone(result)


# ===========================================================================
# Tests: data_handler.py
# ===========================================================================

class TestDataHandler(unittest.TestCase):
    """Tests for watchlist management and serialization helpers."""

    TEST_FILE = "test_watchlist.json"

    def setUp(self):
        """Create a fresh in-memory watchlist and sample book for each test."""
        self.watchlist: dict = {}
        self.book = make_textbook(isbn="978-0000000001")
        self.book.add_listing(make_listing("Amazon", 25.00, "Good"))

    def tearDown(self):
        """Remove any test watchlist file written during tests."""
        if os.path.exists("watchlist.json"):
            os.remove("watchlist.json")

    # --- is_in_watchlist ---

    def test_is_in_watchlist_true(self):
        """is_in_watchlist returns True when the ISBN is present."""
        self.watchlist[self.book.isbn] = self.book
        self.assertTrue(is_in_watchlist(self.watchlist, self.book.isbn))

    def test_is_in_watchlist_false(self):
        """is_in_watchlist returns False when the ISBN is absent."""
        self.assertFalse(is_in_watchlist(self.watchlist, "978-9999999999"))

    # --- add_to_watchlist ---

    def test_add_to_watchlist_adds_book(self):
        """add_to_watchlist stores the book in the watchlist dict."""
        add_to_watchlist(self.watchlist, self.book)
        self.assertIn(self.book.isbn, self.watchlist)

    def test_add_to_watchlist_returns_added_message(self):
        """add_to_watchlist message says 'Added' for a new book."""
        msg = add_to_watchlist(self.watchlist, self.book)
        self.assertIn("Added", msg)

    def test_add_to_watchlist_returns_updated_message(self):
        """add_to_watchlist message says 'Updated' when the book already exists."""
        add_to_watchlist(self.watchlist, self.book)
        msg = add_to_watchlist(self.watchlist, self.book)
        self.assertIn("Updated", msg)

    # --- remove_from_watchlist ---

    def test_remove_from_watchlist_removes_book(self):
        """remove_from_watchlist deletes the book from the watchlist."""
        self.watchlist[self.book.isbn] = self.book
        remove_from_watchlist(self.watchlist, self.book.isbn)
        self.assertNotIn(self.book.isbn, self.watchlist)

    def test_remove_from_watchlist_returns_confirmation(self):
        """remove_from_watchlist returns a message containing the book title."""
        self.watchlist[self.book.isbn] = self.book
        msg = remove_from_watchlist(self.watchlist, self.book.isbn)
        self.assertIn(self.book.title, msg)

    def test_remove_from_watchlist_isbn_not_found(self):
        """remove_from_watchlist returns a 'not found' message for unknown ISBNs."""
        msg = remove_from_watchlist(self.watchlist, "978-9999999999")
        self.assertIn("not found", msg.lower())

    # --- serialization round-trip ---

    def test_listing_serialize_deserialize_roundtrip(self):
        """A Listing survives serialize → deserialize with all fields intact."""
        lst = make_listing("Chegg", 19.99, "Like New", "https://chegg.com", "2025-03-01")
        recovered = _deserialize_listing(_serialize_listing(lst))
        self.assertEqual(recovered.source, lst.source)
        self.assertEqual(recovered.price, lst.price)
        self.assertEqual(recovered.condition, lst.condition)
        self.assertEqual(recovered.url, lst.url)
        self.assertEqual(recovered.timestamp, lst.timestamp)

    def test_watchlist_serialize_deserialize_roundtrip(self):
        """A watchlist dict survives serialize → deserialize with correct data."""
        self.watchlist[self.book.isbn] = self.book
        raw = _serialize_watchlist(self.watchlist)
        recovered = _deserialize_watchlist(raw)
        self.assertIn(self.book.isbn, recovered)
        recovered_book = recovered[self.book.isbn]
        self.assertEqual(recovered_book.title, self.book.title)
        self.assertEqual(len(recovered_book.listings), len(self.book.listings))

    # --- save / load ---

    def test_save_and_load_watchlist(self):
        """save_watchlist followed by load_watchlist returns equivalent data."""
        self.watchlist[self.book.isbn] = self.book
        save_watchlist(self.watchlist)
        loaded = load_watchlist()
        self.assertIn(self.book.isbn, loaded)
        self.assertEqual(loaded[self.book.isbn].title, self.book.title)

    def test_load_watchlist_no_file_returns_empty(self):
        """load_watchlist returns an empty dict when no file exists."""
        if os.path.exists("watchlist.json"):
            os.remove("watchlist.json")
        result = load_watchlist()
        self.assertEqual(result, {})


# ===========================================================================
# Tests: display.py helpers (non-I/O formatting functions)
# ===========================================================================

class TestDisplayHelpers(unittest.TestCase):
    """Tests for pure formatting helpers in display.py."""

    def test_divider_default_length(self):
        """_divider returns a string of the default width (70)."""
        result = _divider()
        self.assertEqual(len(result), 70)

    def test_divider_custom_char_and_width(self):
        """_divider uses the supplied character and width."""
        result = _divider("=", 50)
        self.assertEqual(len(result), 50)
        self.assertTrue(all(c == "=" for c in result))

    def test_table_header_contains_column_names(self):
        """_table_header string includes 'Source', 'Price', and 'Condition'."""
        header = _table_header()
        self.assertIn("Source", header)
        self.assertIn("Price", header)
        self.assertIn("Condition", header)

    def test_listing_row_contains_price_and_source(self):
        """_listing_row output includes the listing's source and price."""
        lst = make_listing("AbeBooks", 14.99)
        row = _listing_row(lst)
        self.assertIn("AbeBooks", row)
        self.assertIn("14.99", row)

    def test_listing_row_contains_url(self):
        """_listing_row output includes the listing URL."""
        lst = make_listing(url="https://abebooks.com/test")
        row = _listing_row(lst)
        self.assertIn("https://abebooks.com/test", row)


# ===========================================================================
# Written Testing Procedure (for I/O functions that cannot be unit-tested)
# ===========================================================================
#
# The following functions in main.py and display.py involve direct console
# I/O (print/input) and cannot be reliably automated with unit tests.
# A human tester should follow these steps to verify them:
#
# --- Function: main() in main.py ---
# 1. Run:  python main.py
# 2. Expected: A help menu is printed listing available commands.
# 3. Type: "search" and press Enter.
#    Expected: A prompt asks for a textbook title or ISBN.
# 4. Type: "Effective Java" and press Enter.
#    Expected: A price comparison table appears with listings from multiple
#    sources, sorted by price, and the best deal is highlighted.
# 5. At the filter menu, type "1" and press Enter.
#    Expected: Listings are shown sorted from lowest to highest price.
# 6. Type "2", then enter "Good".
#    Expected: Only listings with condition "Good" are shown.
# 7. Type "3", then enter "Amazon".
#    Expected: Only Amazon listings are shown.
# 8. Type "4", then enter "30".
#    Expected: Only listings at $30.00 or under are shown.
# 9. Type "5" to add to watchlist.
#    Expected: Confirmation message is printed; watchlist.json is created.
# 10. Type "6" to return to main menu, then type "watchlist".
#    Expected: The saved book appears in the watchlist with its best price.
# 11. Type "quit".
#    Expected: Program exits with a goodbye message.
#
# --- Function: print_no_results() in display.py ---
# 1. At the search prompt, type a nonsense query like "zzzzzznotabook".
#    Expected: A "No results found" message appears with the query echoed.
#
# --- Function: handle_filter_menu() invalid input ---
# 1. At the filter menu, type "99" and press Enter.
#    Expected: An "Invalid option" message appears; the menu re-displays.
# 2. At the max price prompt (option 4), type "abc" (non-numeric).
#    Expected: An "Invalid input" message appears without crashing.
#
# --- Persistence test ---
# 1. Add a book to the watchlist (step 9 above), then quit.
# 2. Re-run python main.py and type "watchlist".
#    Expected: The previously saved book still appears (read from watchlist.json).


if __name__ == "__main__":
    unittest.main(verbosity=2)
