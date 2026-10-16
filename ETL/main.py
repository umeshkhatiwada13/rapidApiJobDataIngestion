import fetchData
import loadDataToSqlite
import viewJobs


def main():
    fetchData.fetch_data()
    loadDataToSqlite.load_jobs_to_sqlite()
    viewJobs.view_jobs()


if __name__ == "__main__":
    main()
