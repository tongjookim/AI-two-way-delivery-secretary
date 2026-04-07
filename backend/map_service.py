import requests

class MapService:
    def __init__(self):
        # 카카오 개발자 센터에서 발급받은 REST API 키를 입력하세요.
        self.kakao_api_key = "kakao-api-key" 
        self.base_url = "https://dapi.kakao.com/v2/local/search/keyword.json"

    def search_top_restaurants(self, menu_keyword, lat=None, lng=None):
        """
        카카오 로컬 API를 사용하여 키워드에 맞는 음식점 3곳을 검색합니다.
        """

        # [수정 1] 넘겨받은 menu_keyword에서 이모지를 제거합니다.
        clean_keyword = menu_keyword.replace("😋", "").replace("🍖", "").replace("🆓", "").strip()

        print(f"[Kakao API] '{clean_keyword}' 검색 요청 (원본: {menu_keyword})")

        headers = {
            "Authorization": f"KakaoAK {self.kakao_api_key}"
        }

        params = {
            "query": clean_keyword,       # [수정 2] 이모지가 제거된 깨끗한 키워드를 사용합니다!
            "category_group_code": "FD6", # 음식점 카테고리만 필터링
            "size": 3,                    # 3개 결과만 가져옴
            "sort": "accuracy"            # 정확도순 정렬
        }

        # [핵심] 위치 정보(lat, lng)가 넘어왔다면 카카오 API 설정 변경
        if lat and lng:
            params["y"] = str(lat)       # 위도 (latitude)
            params["x"] = str(lng)       # 경도 (longitude)
            params["radius"] = 5000      # 5km 반경 내에서만 검색
            params["sort"] = "distance"  # ✨ 내 위치 기준 가장 가까운 순서로 정렬!

        try:
            response = requests.get(self.base_url, headers=headers, params=params)
            response.raise_for_status() # 에러 발생 시 예외 발생
            
            data = response.json()
            documents = data.get('documents', [])

            return [{
                "id": d['id'],
                "name": d['place_name'],
                "address": d['address_name'],
                "phone": d['phone'] or '번호없음',
                # 카카오 API는 distance(거리)를 미터 단위로 내려줍니다.
                "distance": f"{d.get('distance')}m" if d.get('distance') else "",
                "rating": 4.5
            } for d in documents] # [수정 3] docs가 아니라 documents로 순회해야 합니다!

        except Exception as e:
            print(f"API Error: {e}")
            return []

    def get_restaurant_by_id(self, restaurant_id):
        """
        장소 ID를 기반으로 특정 식당의 정보를 반환합니다.
        """
        return {
            "name": "선택된 식당",
            "phone": "010-0000-0000",
            "address": "서울특별시 어딘가"
        }