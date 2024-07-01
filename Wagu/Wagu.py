import sqlite3
import sys
from PyQt5.QtWidgets import *
from PyQt5 import uic
from PyQt5.QtCore import Qt
import re
from datetime import datetime

con = sqlite3.connect('C:\Wagu\wagu.db')
cur = con.cursor()
form_class = uic.loadUiType("main.ui")[0]
global restName
global menuBasket
global priceBasket 
global usingCoupon
global method
global tableWare
global Pay_Price
global allHistory
menuBasket = []
priceBasket = []
usingCoupon = None
method = None
tableWare = None
Pay_Price = 0
allHistory = []

#메인 화면(매장 조회)
class WindowClass(QMainWindow, form_class) :
    def __init__(self) :
        super().__init__()
        self.setupUi(self)
        self.rest_list.itemDoubleClicked.connect(self.openNewWindow)
        rest_list = self.rest_list
        rests = cur.execute("select rest_name from restaurant")

        for row in rests:
            item = QListWidgetItem(row[0])
            rest_list.addItem(item)

    def openNewWindow(self, item):
        global restName
        global menuBasket
        global priceBasket
        menuBasket = []
        priceBasket = []    
        restName = item.text()
        detail_dialog = DetailDialog()
        detail_dialog.exec_()

#메뉴 조회 화면
class DetailDialog(QDialog, uic.loadUiType("detail.ui")[0]):
    def __init__(self) :
        super().__init__()
        self.setupUi(self)
        self.restLable.setText(restName)


        cate = cur.execute(f"SELECT DISTINCT C.CATE_NAME FROM RESTAURANT R JOIN MENU M ON R.REST_ID = M.REST_ID JOIN CATEGORY C ON M.CATE_ID = C.CATE_ID WHERE R.REST_NAME = '{restName}'").fetchall()
        cate_names = [row[0] for row in cate]

        label_list = [self.c1Label, self.c2Label, self.c3Label, self.c4Label, self.c5Label]
        for i, label in enumerate(label_list):
            label.setText(cate_names[i] if cate_names else "")

        for i, label in enumerate(label_list):
            cate_name = label.text()
            query = f"""
                SELECT M.MENU_NAME, M.MENU_PRICE
                FROM RESTAURANT R
                JOIN MENU M ON R.REST_ID = M.REST_ID
                JOIN CATEGORY C ON M.CATE_ID = C.CATE_ID
                WHERE R.REST_NAME = '{restName}' AND C.CATE_NAME = '{cate_name}'
            """
            menu_items = cur.execute(query).fetchall()
            
            menu_list = getattr(self, f"c{i + 1}List")
            menu_list.itemDoubleClicked.connect(self.showAlert)
            
            for menu_item in menu_items:
                menu_name, menu_price = menu_item
                item_text = f"{menu_name}: {menu_price}원"
                item = QListWidgetItem(item_text)
                menu_list.addItem(item)

        minQuery = f"""
            SELECT MINIMUM
            FROM RESTAURANT R
            WHERE R.REST_NAME = '{restName}'
        """
        min_charge = cur.execute(minQuery).fetchone()
        self.minimumLable.setText(str(min_charge[0])+"원")

        self.basketBtn.clicked.connect(self.openBasket)

        couponQuery = f"""
                SELECT C.COUPON_NAME
                FROM RESTAURANT R
                JOIN COUPON C ON R.REST_ID = C.REST_ID
                WHERE R.REST_NAME = '{restName}'
            """
        coupon = cur.execute(couponQuery).fetchone()
        self.couponBtn.setText(str(coupon[0])+" 받기")
        self.couponBtn.clicked.connect(self.getCoupon)

        self.restInfoBtn.clicked.connect(self.openInfo)
        self.reviewBtn.clicked.connect(self.openReview)

        delChargeQuery = f"""
            SELECT DELIVERY_CHARGE
            FROM RESTAURANT
            WHERE REST_NAME = '{restName}'
        """
        delCharge = cur.execute(delChargeQuery).fetchone()

        self.delChargeLable.setText(str(delCharge[0])+"원")
    
    def openReview(self, currentRes):
        global restName
        restName = self.restLable.text()
        review_dialog = ReviewDialog()
        review_dialog.exec_()

    def openInfo(self):
        info_dialog = InfoDialog()
        info_dialog.exec_()

    def getCoupon(self):
        couponExistQuery = f"""
            SELECT *
            FROM COUPON_OWNED O
            JOIN COUPON C ON C.COUPON_ID = O.COUPON_ID
            JOIN RESTAURANT R ON R.REST_ID = C.REST_ID
            WHERE R.REST_NAME = '{restName}'
        """
        couponExist = cur.execute(couponExistQuery).fetchall()
        if couponExist:
            QMessageBox.information(self, "이미 보유한 쿠폰", f"이미 발급 받은 쿠폰입니다.", QMessageBox.Ok)
        else:
            findCouponQuery = f"""
                SELECT COUPON_ID
                FROM COUPON C
                JOIN RESTAURANT R ON R.REST_ID = C.REST_ID
                WHERE R.REST_NAME = '{restName}'
            """
            couponID = cur.execute(findCouponQuery).fetchone()
            
            insertCouponQuery = f"""
                INSERT INTO 'COUPON_OWNED'("COUPON_ID", "UID")
                VALUES
                ('{str(couponID[0])}', 1);
            """
            cur.execute(insertCouponQuery)
            con.commit()

            QMessageBox.information(self, "쿠폰 발급", f"쿠폰 발급 완료", QMessageBox.Ok)
        

    def showAlert(self, item):
        item_text = item.text()
        global priceBasket
        global menuBasket

        menu_name, menu_price_str = item_text.split(':')
        menu_price = int(menu_price_str.replace('원', '').strip())

        if menu_name not in menuBasket:
            menuBasket.append(menu_name)
            priceBasket.append(menu_price)
            QMessageBox.information(self, "장바구니", f"{item_text}\n\n장바구니에 추가했습니다.", QMessageBox.Ok)
        else:
            QMessageBox.information(self, "장바구니", f"{menu_name}이 이미 장바구니에 있습니다.", QMessageBox.Ok)

    def openBasket(self):
        global usingCoupon
        usingCoupon = None
        basket_dialog = BasketDialog()
        basket_dialog.exec_()

#매장 정보 화면
class InfoDialog(QDialog, uic.loadUiType("info.ui")[0]):
    def __init__(self) :
        super().__init__()
        self.setupUi(self)
        restNameLable = self.restNameLable
        restAddrLable = self.restAddrLable
        restNumberLable = self.restNumberLable
        ownerLable = self.ownerLable
        ownerNumLable = self.ownerNumLable

        restNameLable.setText(restName)

        restAddrQuery = f"""
            SELECT REST_ADDRESS
            FROM RESTAURANT
            WHERE REST_NAME = '{restName}'
        """

        restNumberQuery = f"""
            SELECT REST_TEL
            FROM RESTAURANT
            WHERE REST_NAME = '{restName}'
        """

        ownerQuery = f"""
            SELECT O_NAME
            FROM OWNER O
            JOIN RESTAURANT R ON R.OID = O.OID
            WHERE REST_NAME = '{restName}'
        """

        ownerNumQuery = f"""
            SELECT O_NO
            FROM OWNER O
            JOIN RESTAURANT R ON R.OID = O.OID
            WHERE REST_NAME = '{restName}'
        """
        restAddr = cur.execute(restAddrQuery).fetchone()
        restNumber = cur.execute(restNumberQuery).fetchone()
        owner = cur.execute(ownerQuery).fetchone()
        ownerNum = cur.execute(ownerNumQuery).fetchone()

        restAddrLable.setText(str(restAddr[0]))
        restNumberLable.setText(str(restNumber[0]))
        ownerLable.setText(str(owner[0]))
        ownerNumLable.setText(str(ownerNum[0]))


#리뷰 조회 화면
class ReviewDialog(QDialog, uic.loadUiType("review.ui")[0]):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.reviewRestLable.setText(restName + " 리뷰")
        reviewList = self.reviewList

        nickQuery = f"""
            SELECT M.U_NICKNAME
            FROM MEMBER M
            JOIN 'ORDER' O ON O.UID = M.UID
            JOIN REVIEW RV ON RV.ORDER_ID = O.ORDER_ID
            JOIN RESTAURANT RES ON O.REST_ID = RES.REST_ID
            WHERE RES.REST_NAME = '{restName}'
            GROUP BY O.ORDER_ID, M.U_NICKNAME;
        """

        nicks = cur.execute(nickQuery).fetchall()

        for i in range(len(nicks)):
            nickname = nicks[i][0]

            reviewQuery = f"""
            SELECT RV.RATING, RV.CONTENT
            FROM REVIEW RV
            JOIN 'ORDER' O ON O.ORDER_ID = RV.ORDER_ID
            JOIN MEMBER M ON M.UID = O.UID
            JOIN RESTAURANT R ON O.REST_ID = R.REST_ID
            WHERE M.U_NICKNAME = '{nickname}' AND R.REST_NAME = '{restName}'
            GROUP BY O.ORDER_ID, RV.RATING, RV.CONTENT;
            """     
            reviews = cur.execute(reviewQuery).fetchall()
            review = reviews[i]
            rating, content = review

            item_text = f"닉네임: {nickname}\n평점: {rating}\n내용: {content}"
            item = QListWidgetItem(item_text)
            reviewList.addItem(item)


#장바구니 화면
class BasketDialog(QDialog, uic.loadUiType("basket.ui")[0]):
    def __init__(self) :
        super().__init__()
        self.setupUi(self)
        basket_list = self.basketList
        totalLable = self.totalLable
        useCouponBtn = self.useCouponBtn
        couponBox = self.couponBox

        global priceBasket
        global menuBasket

        for i in range(len(menuBasket)):
            menu_name = menuBasket[i]
            menu_price = priceBasket[i]
            item_text = f"{menu_name}: {menu_price}원"
            item = QListWidgetItem(item_text)
            basket_list.addItem(item)

        basket_list.itemDoubleClicked.connect(self.removeItem)

        useCouponBtn.clicked.connect(self.useCoupon)

        ownedQuery = f"""
            SELECT COUPON_NAME
            FROM COUPON C
            JOIN COUPON_OWNED O ON O.COUPON_ID = C.COUPON_ID
            JOIN RESTAURANT R ON C.REST_ID = R.REST_ID
            WHERE REST_NAME = '{restName}'
        """
        ownedCoupon = cur.execute(ownedQuery).fetchall()

        for coupon_name in ownedCoupon:
            item_text = coupon_name[0]
            couponBox.addItem(item_text)

        methodBox = self.methodBox
        methodBox.addItem("신용카드")
        methodBox.addItem("계좌이체")

        tableWareBox = self.tableWareBox
        tableWareBox.addItem("O")
        tableWareBox.addItem("X")

        self.setPrice()

        self.payBtn.clicked.connect(self.payment)
        

    def payment(self):

        selected_method = self.methodBox.currentText()
        selected_tableWare = self.tableWareBox.currentText()

        current_date_time = datetime.now()
        
        global menuBasket

        minQuery = f"""
            SELECT MINIMUM
            FROM RESTAURANT R
            WHERE R.REST_NAME = '{restName}'
        """
        min_charge = cur.execute(minQuery).fetchone()
        if(sum(priceBasket)<min_charge[0]):
            QMessageBox.information(self, "주문 불가", f"주문 금액이 최소 주문 금액보다 작습니다.\n\n 최소 주문 금액: {min_charge[0]}원", QMessageBox.Ok)
        else:

            
            restIdQuery = f""" 
                SELECT REST_ID
                FROM RESTAURANT R
                WHERE R.REST_NAME = '{restName}'
            """

            global menuBasket
            global allHistory

            REST_ID = cur.execute(restIdQuery).fetchone()[0]

            UID = 1
            ORDER_ID = self.get_next_order_id()
            PAY_BY = selected_method
            ORDER_METHOD = "배달"
            ORDER_DATE = current_date_time.strftime('%Y-%m-%d')
            TABLEWARE = selected_tableWare
            QUANTITY = 1


            for menu_name in menuBasket:
                menuInfoQuery = f"""
                    SELECT M.MENU_ID
                    FROM MENU M
                    JOIN RESTAURANT R ON M.REST_ID = R.REST_ID
                    WHERE R.REST_NAME = '{restName}' AND M.MENU_NAME = '{menu_name}'
                """

                menu_info = cur.execute(menuInfoQuery).fetchone()

                if menu_info:
                    MENU_ID = menu_info[0]
                    global Pay_Price

                    insertOrderQuery = f"""
                        INSERT INTO "ORDER" ("ORDER_ID", "REST_ID", "MENU_ID", "UID", "PAY_PRICE", "PAY_BY", "ORDER_METHOD", "ORDER_DATE", "TABLEWARE", "QUANTITY")
                        VALUES ('{ORDER_ID}', '{REST_ID}', '{MENU_ID}', {UID}, {Pay_Price}, '{PAY_BY}', '{ORDER_METHOD}', '{ORDER_DATE}', '{TABLEWARE}', {QUANTITY})
                    """

                    allHistory = [ORDER_ID, PAY_BY, ORDER_METHOD, ORDER_DATE, TABLEWARE]
                    cur.execute(insertOrderQuery)
                    con.commit()
            
            self.close()
            orderCheck_dialog = OrderCheckDialog()
            orderCheck_dialog.exec_()

    
    def get_next_order_id(self):

        cur.execute("SELECT MAX(CAST(SUBSTR(ORDER_ID, 2) AS INTEGER)) FROM 'ORDER'")
        max_order_id = cur.fetchone()[0]
        next_order_id = 'O' + str(max_order_id + 1) if max_order_id is not None else 'O1'
        return next_order_id

    def removeItem(self, item):
        item_text = item.text()
        self.basketList.takeItem(self.basketList.row(item))
        menu_name, price_text = item_text.split(": ")
        price = int(price_text[:-1])

        if menu_name in menuBasket:
            menuBasket.remove(menu_name)

        if price in priceBasket:
            priceBasket.remove(price)

        self.setPrice()

    def setPrice(self):
        global priceBasket
        global usingCoupon
        global Pay_Price

        delChargeQuery = f"""
            SELECT DELIVERY_CHARGE
            FROM RESTAURANT
            WHERE REST_NAME = '{restName}'
        """
        delCharge = cur.execute(delChargeQuery).fetchone()
        
        if usingCoupon:
            sumPrice = sum(priceBasket)+delCharge[0]-usingCoupon
            totalPrice = f"주문금액: {str(sum(priceBasket))}\n배달비: {str(delCharge[0])}\n쿠폰 할인: -{usingCoupon}\n\n총 결제 금액: {sumPrice}"
            self.totalLable.setText(totalPrice)
            Pay_Price = sumPrice
        else:
            sumPrice = sum(priceBasket)+delCharge[0]
            totalPrice = f"주문금액: {str(sum(priceBasket))}\n배달비: {str(delCharge[0])}\n\n총 결제 금액: {sumPrice}"
            self.totalLable.setText(totalPrice)
            Pay_Price = sumPrice

    def useCoupon(self):
        global usingCoupon

        try:
            selected_item = self.couponBox.currentText()
            numbers = re.findall(r'\d+', selected_item)
            usingCoupon = int(numbers[0])
            self.setPrice()
        except:
            QMessageBox.information(self, "쿠폰 사용", f"사용 가능한 쿠폰이 없습니다.", QMessageBox.Ok)



        
        
#주문 내역 조회 화면
class OrderCheckDialog(QDialog, uic.loadUiType("orderCheck.ui")[0]):
    def __init__(self) :
        super().__init__()
        self.setupUi(self)
        global menuBasket
        global priceBasket
        global allHistory

        self.setWindowFlag(Qt.WindowCloseButtonHint, False)
        self.closeBtn.clicked.connect(self.close_window)
        writeBtn = self.writeReviewBtn
        writeBtn.clicked.connect(self.openWrite)

        history = self.orderContentLable
        str = f"주문 번호: {allHistory[0]}\n매장 명: {restName}\n주문 메뉴: "

        for menu_item in menuBasket:
            str+= menu_item
            str+= " "
        str += f"\n주문 가격: {Pay_Price}원\n결제 수단: {allHistory[1]}\n결제 날짜: {allHistory[3]}\n일회용 식기 여부: {allHistory[4]}\n\n\n"

        userQuery = f"""
            SELECT U_NAME, U_ADDRESS, U_PHONE
            FROM MEMBER
            WHERE UID = 1
        """

        userResult = cur.execute(userQuery).fetchone()
        u_name, u_address, u_phone = userResult
        str += f"주문자: {u_name}\n전화번호: {u_phone}\n주소: {u_address}\n\n"

        RiderQuery = f"""
            SELECT R_NAME, R_NUMBER, VEHICLE
            FROM RIDER
            WHERE CAN_DELIVER = '가능'
            ORDER BY RANDOM()
            LIMIT 1;
        """

        RndRider = cur.execute(RiderQuery).fetchone()
        r_name, r_number, vehicle = RndRider

        str += f"배정된 라이더: {r_name}\n전화번호: {r_number}\n배송수단: {vehicle}"

        history.setText(str)

        allHistory += menuBasket
        
        menuBasket = []
        priceBasket = []

        if usingCoupon:
            couponUsed = f"""
            SELECT COUPON_ID FROM COUPON C
            JOIN RESTAURANT R ON R.REST_ID = C.REST_ID
            WHERE REST_NAME = '{restName}';
            """
            getUsedCoupon = cur.execute(couponUsed).fetchone()[0]

            delCoupon = f"""
                DELETE FROM COUPON_OWNED WHERE COUPON_ID = '{getUsedCoupon}'
            """

            cur.execute(delCoupon)

            con.commit()

    def close_window(self):
        self.close()

    def openWrite(self):
        write_dialog = WriteDialog()
        write_dialog.exec_()

#리뷰 작성 화면
class WriteDialog(QDialog, uic.loadUiType("write.ui")[0]):
    def __init__(self) :
        super().__init__()
        self.setupUi(self)
        finishBtn = self.finishBtn
        
        infoLable = self.infoLable
        info = f"{restName} 리뷰 쓰기"
        infoLable.setText(info)
        str = f"매장: {restName}\n메뉴: "

        menus = []
        menus.extend(allHistory[5:])
        for menu in menus:
            str += menu + " "

        finishBtn.clicked.connect(self.finish)

    def finish(self):

        REVIEW_ID = self.get_next_review_id()
        ORDER_ID = allHistory[0]
        RATING = int(self.rateBox.currentText())
        CONTENT = self.editText.toPlainText()

        writeQuery = f"""
            INSERT INTO "REVIEW" ("REVIEW_ID", "ORDER_ID", "RATING", "CONTENT") 
            VALUES ('{REVIEW_ID}', '{ORDER_ID}', {RATING}, '{CONTENT}');
        """
        cur.execute(writeQuery)
        con.commit()

        self.close()

    def get_next_review_id(self):

        cur.execute("SELECT MAX(CAST(SUBSTR(REVIEW_ID, 2) AS INTEGER)) FROM 'REVIEW'")
        max_review_id = cur.fetchone()[0]

        next_review_id = 'V' + str(max_review_id + 1) if max_review_id is not None else 'V1'
        return next_review_id


if __name__ == "__main__" :
    app = QApplication(sys.argv)
    myWindow = WindowClass() 
    myWindow.show()
    app.exec_()