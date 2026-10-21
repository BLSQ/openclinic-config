<%@page errorPage="/includes/error.jsp"%>
<%@include file="/includes/validateUser.jsp"%>
<%
    if(activePatient!=null && activePatient.personid.length()>0){
        AdminPrivateContact apc = ScreenHelper.getActivePrivate(activePatient);

        if(apc!=null){
            String sCountry = "&nbsp;";
            if(checkString(apc.country).trim().length()>0){
                sCountry = getTran(request,"Country",apc.country,sWebLanguage);
            }

            String sProvince = "&nbsp;";
            if(checkString(apc.province).trim().length()>0){
                sProvince = getTran(request,"province",apc.province,sWebLanguage);
            }
            
            %>
                <table width="100%" cellspacing="1" class="list" style="border-top:none;">
                    <%=
                        setRow("Web.admin","addresschangesince",apc.begin,sWebLanguage)+
                        (
                            be.openclinic.core.db.Config.getConfigInt("showAdminPrivateCountry",1)==0?"":
                            setRow(request,"Web","country",sCountry,sWebLanguage)
                        )
                       +(
                            be.openclinic.core.db.Config.getConfigInt("showAdminPrivateDistrict",1)==0?"":
                            setRow(request,"Web","district",apc.district,sWebLanguage)
                        )
                       +(
                            be.openclinic.core.db.Config.getConfigInt("showAdminPrivateZipcode",1)==0?"":
                            setRow(request,"Web","zipcode",apc.zipcode,sWebLanguage)
                        )
                       +(
                            be.openclinic.core.db.Config.getConfigInt("showAdminPrivateProvince",1)==0?"":
                            setRow(request,"Web","province",sProvince,sWebLanguage)
                        )
                       +(
                            be.openclinic.core.db.Config.getConfigInt("showAdminPrivateCity",1)==0?"":
                            setRow(request,"Web","city",apc.city,sWebLanguage)
                        )
                       +(
                            be.openclinic.core.db.Config.getConfigInt("showAdminPrivateSector",1)==0?"":
                            setRow(request,"Web","sector",apc.sector,sWebLanguage)
                        )
                       +(
                            be.openclinic.core.db.Config.getConfigInt("showAdminPrivateCell",1)==0?"":
                            setRow(request,"Web","cell",apc.cell,sWebLanguage)
                        )
                       +(
                            be.openclinic.core.db.Config.getConfigInt("showAdminPrivateAddress",1)==0?"":
                            setRow(request,"Web","address",apc.address,sWebLanguage)
                        )
                       +(
                            be.openclinic.core.db.Config.getConfigInt("showAdminPrivateEmail",1)==0?"":
                            setRow(request,"Web","email",apc.email,sWebLanguage)
                        )
                       +(
                            be.openclinic.core.db.Config.getConfigInt("showAdminPrivateTelephone",1)==0?"":
                            setRow(request,"Web","telephone",apc.telephone,sWebLanguage)
                        )
                       +(
                            be.openclinic.core.db.Config.getConfigInt("showAdminPrivateMobile",1)==0?"":
                            setRow(request,"Web","mobile",apc.mobile,sWebLanguage)
                        )
                       +(
                            be.openclinic.core.db.Config.getConfigInt("showAdminPrivateFunction",1)==0?"":
                            setRow(request,"Web","function",apc.businessfunction,sWebLanguage)
                        )
                       +(
                            be.openclinic.core.db.Config.getConfigInt("showAdminPrivateBusiness",1)==0?"":
                            setRow(request,"Web","business",apc.business,sWebLanguage)
                        )
                       +(
                            be.openclinic.core.db.Config.getConfigInt("showAdminPrivateComment",1)==0?"":
                            setRow(request,"Web","comment",apc.comment,sWebLanguage)
                        )
					%>
                    <tr height='1'><td width='<%=sTDAdminWidth%>'/></tr>
                </table>
            <%
        }
        else{
        	%><%=getTran(request,"web","noRecordsFound",sWebLanguage)%><%
        }
    }
%>

<%-- BUTTONS -------------------------------------------------------------------------------------%>
<%
    String sShowButton = checkString(request.getParameter("ShowButton"));
    if(!sShowButton.equals("false")){
        %>
            <%=ScreenHelper.alignButtonsStart()%>
                <input type="button" class="button" value="<%=getTranNoLink("Web","history",sWebLanguage)%>" name="ButtonHistoryPrivate" onclick="parent.location='patienthistory.do?ts=<%=getTs()%>&contacttype=private'">&nbsp;
                <%
                    if (activeUser.getAccessRight("patient.administration.edit")){
                        %><input type="button" class="button" onclick="window.location.href='<c:url value="/patientedit.do"/>?Tab=AdminPrivate&ts=<%=getTs()%>'" value="<%=getTranNoLink("Web","edit",sWebLanguage)%>"><%
                    }
                %>
            <%=ScreenHelper.alignButtonsStop()%>
        <%
    }
%>