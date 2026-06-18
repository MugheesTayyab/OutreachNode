import os
import unittest
from tools.excel_tool import read_csv, write_excel
from tools.search_tool import search_person, search_company_news
from tools.wiki_tool import get_company_summary
from config.settings import INPUT_DIR

class TestTools(unittest.TestCase):
    
    def test_csv_reader_and_writer(self):
        # Create a small temp CSV file for testing
        temp_csv = os.path.join(INPUT_DIR, "temp_test_prospects.csv")
        with open(temp_csv, "w", encoding="utf-8") as f:
            f.write("name,email,company,title,linkedin_url\n")
            f.write("Test User,test@example.com,Example Corp,CTO,https://linkedin.com/in/test\n")
            
        prospects = read_csv(temp_csv)
        self.assertEqual(len(prospects), 1)
        self.assertEqual(prospects[0]["name"], "Test User")
        self.assertEqual(prospects[0]["company"], "Example Corp")
        
        # Test Excel writing
        temp_excel = os.path.join(INPUT_DIR, "temp_test_output.xlsx")
        write_excel(prospects, temp_excel)
        self.assertTrue(os.path.exists(temp_excel))
        
        # Clean up files
        if os.path.exists(temp_csv):
            os.remove(temp_csv)
        if os.path.exists(temp_excel):
            os.remove(temp_excel)

    def test_search_person(self):
        # We test that search_person returns results or uses fallback
        results = search_person("Sundar Pichai", "Google")
        self.assertTrue(isinstance(results, list))
        self.assertTrue(len(results) > 0)

    def test_search_company_news(self):
        news = search_company_news("Microsoft")
        self.assertTrue(isinstance(news, list))
        self.assertTrue(len(news) > 0)
        self.assertTrue("title" in news[0])

    def test_get_company_summary(self):
        summary = get_company_summary("Microsoft")
        self.assertTrue(isinstance(summary, str))

if __name__ == '__main__':
    unittest.main()
